import os
from os import path
import time
from functools import wraps
from urllib.parse import urlencode, parse_qsl
from zlib import adler32
from io import BytesIO
import mimetypes

from flask import current_app, Response, request
from flask import render_template, jsonify, send_file as _send_file
from werkzeug.exceptions import NotFound

from .core import main

from ..util import get_version, get_project_url
from ..util import surmise_domain, replace_all, logger, hash_dict, abspath


MT_PAC = 'application/x-ns-proxy-autoconfig'
MT_TXT = 'text/plain'
mimetypes.add_type(MT_PAC, '.pac')


def query2replacements(query):
    if isinstance(query, str):
        query = dict(parse_qsl(query))
    replacements = {}
    for k, v in query.items():
        if k.startswith('__') and k.endswith('__'):
            replacements[k] = v
    return replacements


def replacements2query(replacements):
    return urlencode(sorted(replacements.items()))


def guess_mimetype(filename, raw):
    if raw:
        return MT_TXT
    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype or MT_TXT


def send_file(filename, replacements={}, raw=False):
    # 忽略文件名以`_`开始的文件
    if filename.startswith('_'):
        raise NotFound()

    filename = abspath(filename, base=current_app.config.options.target)

    if not path.isfile(filename):
        raise NotFound()

    mimetype = guess_mimetype(filename, raw)

    if not replacements:
        return _send_file(filename, mimetype=mimetype)

    replacements.update(query2replacements(request.values))

    try:
        with open(filename, 'r') as fp:
            content = fp.read()
            content = replace_all(content, replacements)
    except Exception:
        logger.error(f'Send file fail. {filename}', exc_info=True)
        raise NotFound()

    data = BytesIO(content.encode())

    # NOTE: BytesIO方式不会自动生成etag, 需手动生成
    o_stat = os.stat(filename)
    check = adler32(filename.encode()) & 0xFFFFFFFF
    rep_hash = hash_dict(replacements)
    etag = f'{o_stat.st_mtime}-{data.getbuffer().nbytes}-{check}-{rep_hash}'

    return _send_file(data, etag=etag, mimetype=mimetype)


def is_authorized():
    if not current_app.config.options.auth_token:
        return True

    auth_token = request.headers.get('Token', None) or \
        request.values.get('token', None) or request.values.get('t', None)
    if auth_token == current_app.config.options.auth_token:
        return True

    return False


def authorized(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_authorized():
            return func(*args, **kwargs)
        return current_app.make_response(('Unauthorized.', 401))
    return wrapper


def make_res_data(data={}, code=0, msg='成功'):
    return jsonify({'data': data, 'code': code, 'msg': msg})


@main.before_request
def load_domains():
    if not current_app.extensions['genpac'].domains_outdate:
        return
    try:
        with open(current_app.config.options._private.domain_file) as fp:
            domains = {'p': [], 'd': []}
            for line in fp.readlines():
                t, d = line.split(',')
                domains[t.strip()].append(d.strip())
            current_app.extensions['genpac'].domains_proxy = domains['p']
            current_app.extensions['genpac'].domains_direct = domains['d']
            current_app.extensions['genpac'].domains_outdate = False
            logger.info('Domains loaded.')
    except Exception:
        logger.error('Domains load fail.', exc_info=True)


@main.app_template_global('powered_by')
def powered_by():
    try:
        if current_app.extensions['genpac'].last_builded <= 0:
            statinfo = os.stat(current_app.config.options._private.domain_file)
            current_app.extensions['genpac'].last_builded = statinfo.st_mtime
    except Exception:
        build_date = '-'
    else:
        build_date = time.strftime(
            '%Y-%m-%d %H:%M:%S',
            time.localtime(current_app.extensions['genpac'].last_builded))
    ver = get_version()
    proj_url = get_project_url()
    return f'Last Builded: {build_date}&nbsp;&nbsp;&nbsp;Powered by <a href="{proj_url}">GenPAC v{ver}</a>'


@main.route('/')
def index():
    return render_template('index.j2',
                           ip_srvs=current_app.config.options.ip_srvs)


@main.route('/file/<filename>')
@main.route('/file/raw/<filename>', defaults={'raw': True})
@authorized
def get_file(filename, raw=False):
    return send_file(filename, raw=raw)


@main.route('/s/<string:code>')
@main.route('/s/raw/<string:code>', defaults={'raw': True})
@authorized
def shortener(code, raw=False):
    try:
        cfg = current_app.config.options.shortener.get(code)
        source = cfg.get('source')
    except Exception:
        logger.warning(f'shortener[{code}] ERROR:', exc_info=True)
        return NotFound()

    return send_file(source, replacements=cfg, raw=raw)


@main.route('/list/', methods=['GET'])
def view_gfwlist():
    return send_file(current_app.config.options._private.list_file)


@main.route('/ip/')
def show_ip():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(',')[0]
    return Response(f'{ip}\n',
                    mimetype="text/plain",
                    headers={'X-Your-Ip': ip,
                             'Access-Control-Allow-Origin': '*'})


@main.route('/rules/', methods=['GET'])
def rules():
    if not current_app.config.options.server_rule_enabled:
        return NotFound()

    content = ''
    try:
        with open(current_app.config.options._private.server_rule_file) as fp:
            content = fp.read()
    except Exception:
        pass

    return render_template('rules.j2',
                           content=content,
                           token=request.values.get('token', ''))


@main.route('/api/test/', methods=['GET', 'POST'])
def view_api_test():
    def gen_data(url, domain):
        return make_res_data(data={'d': domain in data.domains_direct,
                                   'p': domain in data.domains_proxy,
                                   'domain': domain,
                                   'url': url})

    url = request.values.get('url', None)
    if not url:
        return make_res_data(code=1, msg='地址不能为空')

    data = current_app.extensions['genpac']
    # 先带子域名 再顶级域名
    domain = surmise_domain(url, True)
    if domain in data.domains_direct or domain in data.domains_proxy:
        return gen_data(url, domain)
    domain = surmise_domain(url, False)
    return gen_data(url, domain)


@main.route('/api/rule-update/', methods=['POST'])
def view_api_rule_update():
    if not current_app.config.options.server_rule_enabled:
        return make_res_data(code=404, msg='服务端用户规则未启用')

    if not is_authorized():
        return make_res_data(code=401, msg='未授权, token错误')

    try:
        content = request.form.get('rules', '')
        with open(current_app.config.options._private.server_rule_file, 'w') as fp:
            fp.write(content.strip())
        return make_res_data()
    except Exception as e:
        return make_res_data(code=1, msg=f'出错了, {e}')
