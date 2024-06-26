import os
import copy
import argparse

from flask import Flask, Blueprint
from flask_apscheduler import APScheduler

from ..config import Config
from ..util import get_version
from ..util import Namespace
from ..util import exit_error, FatalError, mktemp
from ..util import logger, conv_bool, conv_list, conv_path
from .base import init_genpac
from .build import start_watch, autobuild_task

_SERVER_RULE_FILENAME = '_server_rules.txt'
_DEFAULT_OPTIONS = Namespace(
    config_file=None, auth_token=None,
    autobuild_interval=86400, build_on_start=True,
    watch_enabled=True, watch_files=set(), target_path=None,
    server_rule_enabled=True, shortener={},
    ip_srvs={'inland': 'https://4.ipw.cn',
             'abroad': 'https://4.icanhazip.com',
             'gfwed': '//jeekerip.appspot.com'},
    # 私有 不会被更改
    _private=Namespace(
        domain_file=mktemp(),
        list_file=mktemp(),
        server_rule_file='',
        protected_files=set()
    ))

main = Blueprint('main', __name__, static_folder='static')
scheduler = APScheduler()


def create_app(config_file=None):
    from . import view  # noqa: F401
    app = Flask(__name__)

    try:
        config_file = config_file or os.environ.get('GENPAC_CONFIG')
        load_config(app, config_file)
    except FatalError as e:
        exit_error(e)

    app.register_blueprint(main)

    app.extensions['genpac'] = Namespace(
        last_builded=0,
        domains_proxy=[], domains_direct=[], domains_outdate=True)

    if app.config.options.watch_enabled:
        start_watch(app)

    scheduler.init_app(app)
    if app.config.options.build_on_start:
        scheduler.add_job('build_starting', autobuild_task, args=(app,), kwargs={'event': 'START'},
                          misfire_grace_time=30)
    if app.config.options.autobuild_interval > 0:
        scheduler.add_job('auto_build', autobuild_task, args=(app,),
                          max_instances=1, misfire_grace_time=30,
                          trigger='interval',
                          seconds=app.config.options.autobuild_interval)
    scheduler.start()

    # if app.config.options.autobuild_interval > 0 or \
    #         app.config.options.watch_enabled:
    #     start_watch(app)
    # elif app.config.options.build_on_start:
    #     build(app)

    return app


def load_config(app, config_file):
    if not config_file:
        raise FatalError('服务模式: 未设置配置文件，可通过环境变量`GENPAC_CONFIG`指定.')
    if not os.path.exists(conv_path(config_file)):
        raise FatalError(f'服务模式: 配置文件不存在: {config_file}')

    options = copy.deepcopy(_DEFAULT_OPTIONS)
    cfg = {}

    def _val(key, default, *convs):
        if key not in cfg:
            return default
        val = cfg[key]
        for conv in convs:
            val = conv(val)
        return val

    def _update(attr, *convs, **kwargs):
        if not hasattr(options, attr):
            logger.warn(f'ATTR MISSING: {attr}')
            return
        key = kwargs.get('key', attr.strip().replace('_', '-'))
        default = kwargs['default'] if 'default' in kwargs else \
            getattr(options, attr)
        val = _val(key, default, *convs)
        setattr(options, attr, val)

    options.config_file = conv_path(config_file)

    config = Config()
    config.read(options.config_file)
    cfg = config.section('server') or {}

    _update('auth_token')
    _update('build_on_start', conv_bool)
    _update('autobuild_interval', int)
    _update('watch_enabled', conv_bool)
    _update('watch_files', conv_list, conv_path, set,
            key='watch-extra-files')

    # 默认target_path与配置文件同目录
    _update('target_path', conv_path,
            default=os.path.dirname(options.config_file))
    prepare_target(options.target_path)

    _update('server_rule_enabled', conv_bool)
    server_rule_file = os.path.join(options.target_path, _SERVER_RULE_FILENAME)
    options._private.server_rule_file = server_rule_file
    options._private.protected_files.add(server_rule_file)
    if options.server_rule_enabled:
        prepare_server_rule(server_rule_file)

    # 侦测IP的服务器列表
    options.ip_srvs['inland'] = _val('ip.inland', options.ip_srvs['inland'])
    options.ip_srvs['abroad'] = _val('ip.abroad', options.ip_srvs['abroad'])
    options.ip_srvs['gfwed'] = _val('ip.gfwed', options.ip_srvs['gfwed'])

    cfg = config.sections('server-shortener', 'name')
    for k in cfg:
        if k.get('name'):
            options.shortener[k['name']] = k

    # 如果允许监控文件更改
    if options.watch_enabled:
        gp = init_genpac(options)
        # 添加config_file到监控列表
        options.watch_files.add(options.config_file)
        if options.server_rule_enabled:
            # 添加服务器上的规则文件
            options.watch_files.add(server_rule_file)
        # 添加user_rule_from到监控文件列表
        for job in gp.walk_jobs():
            options._private.protected_files |= set([job.output, job.gfwlist_local, job.gfwlist_decoded_save])
            options.watch_files.update(job.user_rule_from)

    app.config.options = options
    logger.debug(app.config.options)


def prepare_target(target):
    if os.path.exists(target):
        if not os.path.isdir(target):
            exit_error(f'target_path`{target}`必须是一个目录')
    else:
        try:
            os.makedirs(target)
        except Exception as e:
            exit_error(f'创建target_path`{target}`失败: {e}')


def prepare_server_rule(file):
    if os.path.exists(file):
        return
    try:
        with open(file, 'w') as fp:
            fp.write('# GenPAC Server rules\n\n')
    except Exception as e:
        exit_error(f'创建服务端规则文件`{file}`失败: {e}')


def run():
    parser = argparse.ArgumentParser(
        prog='genpac.server',
        formatter_class=argparse.RawTextHelpFormatter,
        description='genpac的服务端模式',
        argument_default=argparse.SUPPRESS,
        add_help=False)
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {get_version()}',
                        help='版本信息')
    parser.add_argument('--help', action='help',
                        help='帮助信息')
    parser.add_argument('-h', '--host', metavar="HOST", default='0.0.0.0',
                        help='绑定IP, 默认: 0.0.0.0')
    parser.add_argument('-p', '--port', metavar="PORT", default=8000,
                        help='绑定端口，默认: 8000')
    parser.add_argument('-c', '--config', metavar='FILE', default=None,
                        help='配置文件，也可使用环境变量`GENPAC_CONFIG`')
    args = parser.parse_args()

    app = create_app(args.config)
    app.run(host=args.host, port=args.port)
