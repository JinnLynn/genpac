import imp
import os
import copy
import tempfile

from flask import Flask, Blueprint
from flask_apscheduler import APScheduler

from .. import Namespace, Config, GenPAC, FatalError, formater, FmtBase
from ..util import exit_error
from ..util import logger, conv_bool, conv_list, conv_path
from .build import start_watch, build, autobuild_task

_DEFAULT_OPTIONS = Namespace(
    config_file=None, auth_token=None,
    autobuild_interval=86400, build_on_start=True,
    watch_enabled=True, watch_files=set(), target_path=None,
    server_rule_enabled=True, server_rule_file='server-rules.txt',
    pacs={}, shortener={},
    ip_srvs={'inland': 'https://4.ipw.cn',
             'abroad': 'https://4.icanhazip.com',
             'gfwed': '//jeekerip.appspot.com'},
    # 私有 不会被更改
    _private=Namespace(
        domain_file=tempfile.mktemp(),
        list_file=tempfile.mktemp()
    ))

main = Blueprint('main', __name__, static_folder='static')
scheduler = APScheduler()


def create_app(config_file=None):
    from . import view  # noqa: F401
    app = Flask(__name__)

    try:
        config_file = config_file or os.environ.get('GENPAC_CONFIG')
        read_config(app, config_file)
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


def read_config(app, config_file):
    if not config_file:
        raise FatalError('未设置配置文件，可通过环境变量`GENPAC_CONFIG`指定.')
    if not os.path.exists(conv_path(config_file)):
        raise FatalError('配置文件不存在: {}'.format(config_file or ''))

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
            logger.warn('ATTR MISSING: {}'.format(attr))
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

    _update('server_rule_enabled', conv_bool)
    _update('server_rule_file', conv_path,
            default=os.path.join(options.target_path,
                                 options.server_rule_file))
    if options.server_rule_enabled and \
            not os.path.exists(options.server_rule_file):
        with open(options.server_rule_file, 'w') as fp:
            fp.write('# GenPAC Server rules\n\n')

    # 侦测IP的服务器列表
    options.ip_srvs['inland'] = _val('ip.inland', options.ip_srvs['inland'])
    options.ip_srvs['abroad'] = _val('ip.abroad', options.ip_srvs['abroad'])
    options.ip_srvs['gfwed'] = _val('ip.gfwed', options.ip_srvs['gfwed'])

    cfg = config.section('server-pac')
    for k in cfg.keys():
        options.pacs[k] = cfg[k].strip('"')

    cfg = config.section('server-shortener')
    for k in cfg.keys():
        options.shortener[k] = cfg[k].strip('"')

    # 如果允许监控文件更改
    if options.watch_enabled:
        gp = GenPAC(config_file=options.config_file, argv_enabled=False)
        # 添加config_file到监控列表
        options.watch_files.add(options.config_file)
        if options.server_rule_enabled:
            # 添加服务器上的规则文件
            options.watch_files.add(options.server_rule_file)
        # 添加user_rule_from到监控文件列表
        gp.parse_options()
        for job in gp.walk_jobs():
            options.watch_files.update(job.user_rule_from)

    app.config.options = options
    logger.debug(app.config.options)


@formater('genpac-server-domains')
class FmtDomains(FmtBase):
    def __init__(self, *args, **kwargs):
        super(FmtDomains, self).__init__(*args, **kwargs)

    def generate(self, replacements):
        gfwed = ['p,{}'.format(s) for s in self.gfwed_domains]
        ignored = ['d,{}'.format(s) for s in self.ignored_domains]
        return '\n'.join(gfwed + ignored).strip()
