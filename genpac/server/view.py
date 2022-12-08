import os
import time
from functools import wraps
from urllib.parse import urlencode

from flask import current_app, Response, request
from flask import render_template, jsonify
from werkzeug.urls import url_decode

from .core import main

from .. import __version__, __project_url__
from ..util import surmise_domain, replace_all, logger


def query2replacements(query):
    if isinstance(query, str):
        query = url_decode(query)
    replacements = {}
    for k, v in query.items():
        if k.startswith('__') and k.endswith('__'):
            replacements[k] = v
    return replacements


def replacements2query(replacements):
    return urlencode(sorted(replacements.items()))


def send_file(filename, replacements={}, mimetype=None, add_etags=True):
    # 忽略文件名以`_`开始的文件
    if filename.startswith('_'):
        return current_app.make_response(('Not Found.', 404))

    replacements.update(query2replacements(request.values))

    if not os.path.isabs(filename):
        filename = os.path.abspath(
                    os.path.join(
                        current_app.config.options.target_path,
                        filename))
    try:
        with open(filename, 'r') as fp:
            content = fp.read()

        if replacements:
            content = replace_all(content, replacements)

        resp = current_app.make_response(content)
        resp.mimetype = mimetype or 'text/plain'
        resp.last_modified = os.path.getmtime(filename)
        resp.add_etag()
        return resp
    except Exception as e:
        logger.error('Send file fail.', exc_info=True)

    return current_app.make_response(('Not Found.', 404))


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
    except Exception as e:
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
    return 'Last Builded: {}&nbsp;&nbsp;&nbsp;' \
            'Powered by <a href="{}">GenPAC v{}</a>'.format(build_date,
                                                            __project_url__,
                                                            __version__)


@main.route('/', methods=['GET'])
def index():
    return render_template('index.html',
                           ip_srvs=current_app.config.options.ip_srvs)


@main.route('/pac/<location>/', methods=['GET'])
@authorized
def get_pac(location):
    proxy = current_app.config.options.pacs.get(location) or location
    return send_file('pac.tpl', replacements={'__PROXY__': proxy},
                     mimetype='application/javascript')


@main.route('/file/<filename>', methods=['GET'])
@authorized
def get_file(filename):
    return send_file(filename)


@main.route('/rules/', methods=['GET'])
def rules():
    if not current_app.config.options.server_rule_enabled:
        return current_app.make_response(('Not Found.', 404))

    content = ''
    try:
        with open(current_app.config.options.server_rule_file) as fp:
            content = fp.read()
    except Exception:
        pass

    return render_template('rules.html',
                           content=content,
                           token=request.values.get('token', ''))


@main.route('/s/<code>', methods=['GET'])
@authorized
def shortener(code):
    try:
        code_cfg = current_app.config.options.shortener.get(code)
        cfgs = code_cfg.split(' ')
        cfgs.append('')
        filename, query = cfgs[0:2]
    except Exception as e:
        logger.warning('shortener[{}] ERROR:'.format(code), exc_info=True)
        return current_app.make_response(('', 404))

    rms = query2replacements(query)
    return send_file(filename, replacements=rms)


@main.route('/list/', methods=['GET'])
def view_gfwlist():
    return send_file(current_app.config.options._private.list_file)


@main.route('/ip/')
def show_ip():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(',')[0]
    return Response(
        '{}\n'.format(ip), mimetype="text/plain",
        headers={'X-Your-Ip': ip,
                 'Access-Control-Allow-Origin': '*'})


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
        with open(current_app.config.options.server_rule_file, 'w') as fp:
            fp.write(content.strip())
        return make_res_data()
    except Exception as e:
        return make_res_data(code=1, msg='出错了, {}'.format(e))
