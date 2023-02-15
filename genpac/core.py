import os
import sys
import argparse
import re
import time
from datetime import datetime, timedelta
import copy
from pprint import pprint  # noqa: F401
from collections import OrderedDict
from urllib.request import Request, urlopen
import socket

import socks
from socks import PROXY_TYPES as _PROXY_TYPES

from . import __version__, __project_url__
from .config import Config
from .deprecated import check_deprecated_args, check_deprecated_config
from .util import surmise_domain, b64decode
from .util import Error, FatalError, FatalIOError
from .util import exit_error, exit_success
from .util import abspath, open_file, read_file, write_file
from .util import get_resource_path, get_resource_data
from .util import conv_bool, conv_list, conv_lower, conv_path
from .util import logger


_GFWLIST_URL = \
    'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'


class Namespace(argparse.Namespace):
    def __init__(self, **kwargs):
        self.update(**kwargs)

    def update(self, **kwargs):
        keys = [k.strip().replace('-', '_') for k in kwargs.keys()]
        self.__dict__.update(**dict(zip(keys, kwargs.values())))

    def dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class GenPAC(object):
    # 格式化器列表
    _formaters = OrderedDict()

    def __init__(self, config_file=None, argv_enabled=True):
        super(GenPAC, self).__init__()
        self.config_file = config_file
        self.argv_enabled = argv_enabled

        self.default_opts = {}
        self.init_dest = None
        self.jobs = []
        self.extra_rules = []
        self.extra_jobs = []

    @classmethod
    def add_formater(cls, name, fmt_cls, **options):
        # TODO: 检查cls是否合法
        fmt_cls._name = name
        fmt_cls._desc = options.pop('desc', None)
        cls._formaters[name] = {'cls': fmt_cls,
                                'options': options}

    @classmethod
    def walk_formaters(cls, attr, *args, **kargs):
        for fmter in cls._formaters.values():
            getattr(fmter['cls'], attr)(*args, **kargs)

    def parse_args(self):
        # 如果某选项同时可以在配置文件和命令行中设定，则必须使default=None
        # 以避免命令行中即使没指定该参数，也会覆盖配置文件中的值
        # 原因见parse_config() -> update(name, key, default=None)
        parser = argparse.ArgumentParser(
            prog='genpac',
            formatter_class=argparse.RawTextHelpFormatter,
            description='获取gfwlist生成多种格式的翻墙工具配置文件, '
                        '支持自定义规则',
            epilog=get_resource_data('res/rule-syntax.txt'),
            argument_default=argparse.SUPPRESS,
            add_help=False)
        parser.add_argument(
            '-v', '--version', action='version',
            version='%(prog)s {}'.format(__version__),
            help='版本信息')
        parser.add_argument(
            '-h', '--help', action='help',
            help='帮助信息')
        parser.add_argument(
            '--init', nargs='?', const=True, default=False, metavar='PATH',
            help='初始化配置和用户规则文件')

        group = parser.add_argument_group(
            title='通用参数')
        group.add_argument(
            '--format', type=lambda s: s.lower(),
            choices=GenPAC._formaters.keys(),
            help='生成格式, 只有指定了格式, 相应格式的参数才作用')
        group.add_argument(
            '--gfwlist-url', metavar='URL',
            help='gfwlist网址，无此参数或URL为空则使用默认地址, URL为-则不在线获取')
        group.add_argument(
            '--gfwlist-local', metavar='FILE',
            help='本地gfwlist文件地址, 当在线地址获取失败时使用')
        group.add_argument(
            '--gfwlist-update-local', action='store_true',
            help='当在线gfwlist成功获取且--gfwlist-local参数存在时, '
                 '更新gfwlist-local内容')
        group.add_argument(
            '--gfwlist-disabled', action='store_true',
            help='禁用gfwlist')
        group.add_argument(
            '--gfwlist-decoded-save', metavar='FILE',
            help='保存解码后的gfwlist, 仅用于测试')

        group.add_argument(
            '--user-rule', action='append', metavar='RULE',
            help='自定义规则, 允许重复使用或在单个参数中使用`,`分割多个规则，如:\n'
                 '  --user-rule="@@sina.com" --user-rule="||youtube.com"\n'
                 '  --user-rule="@@sina.com,||youtube.com"')
        group.add_argument(
            '--user-rule-from', action='append', metavar='FILE',
            help='从文件中读取自定义规则, 使用方法如--user-rule')
        group.add_argument(
            '-o', '--output', metavar='FILE',
            help='输出到文件, 无此参数或FILE为-, 则输出到stdout')
        group.add_argument(
            '-c', '--config-from', default=None, metavar='FILE',
            help='从文件中读取配置信息')
        group.add_argument(
            '--template', metavar='FILE', help='自定义模板文件')

        group.add_argument(
            '--proxy', metavar='PROXY',
            help='在线获取外部数据时的代理, 如果可正常访问外部地址, 则无必要使用该选项\n'
                 '格式: [PROTOCOL://][USERNAME:PASSWORD@]HOST:PORT \n'
                 '其中协议、用户名、密码可选, 默认协议 http, 支持协议: http socks5 socks4 socks 如:\n'
                 '  127.0.0.1:8080\n'
                 '  SOCKS5://127.0.0.1:1080\n'
                 '  SOCKS5://username:password@127.0.0.1:1080\n')

        # 检查弃用参数 警告
        check_deprecated_args()

        self.__class__.walk_formaters('arguments', parser)
        return parser.parse_args()

    def read_config(self, config_file):
        if not config_file:
            return [{}], {}
        try:
            cfg = Config()
            cfg.read(config_file)
            return (
                cfg.sections('job', sub_section_key='format') or [{}],
                cfg.section('config') or {})
        except Exception:
            raise FatalError('配置文件{}读取失败'.format(config_file))

    def update_opt(self, args, cfgs, key,
                   default=None, conv=None, dest=None, **kwargs):
        conv = conv or []
        if not isinstance(conv, list):
            conv = [conv]

        if dest is None:
            dest = key.replace('-', '_').lower()

        if hasattr(args, dest):
            v = getattr(args, dest)
        else:
            replaced = kwargs.get('replaced')
            if key in cfgs:
                v = cfgs[key]
            elif replaced and replaced in cfgs:
                v = cfgs[replaced]
            else:
                v = default

        if isinstance(v, str):
            v = v.strip(' \'\t"')

        for c in conv:
            v = c(v)

        return dest, v

    def parse_options(self):
        args = self.parse_args() if self.argv_enabled else Namespace()
        self.init_dest = args.init if hasattr(args, 'init') else None
        config_file = args.config_from if hasattr(args, 'config_from') else \
            self.config_file

        cfgs, self.default_opts = self.read_config(config_file)

        opts = {}
        opts['format'] = {'conv': conv_lower}

        opts['gfwlist-url'] = {'default': _GFWLIST_URL}
        opts['gfwlist-local'] = {'conv': conv_path}
        opts['gfwlist-disabled'] = {'conv': conv_bool}
        opts['gfwlist-update-local'] = {'conv': conv_bool}
        opts['gfwlist-decoded-save'] = {'conv': conv_path}

        opts['user-rule'] = {'conv': conv_list}
        opts['user-rule-from'] = {'conv': [conv_list, conv_path]}

        opts['output'] = {}
        opts['template'] = {'conv': conv_path}
        opts['proxy'] = {}

        opts['_order'] = {'conv': int, 'default': 0}

        self.walk_formaters('config', opts)

        self.clear_jobs()

        # 当配置没有[job]节点且参数没有--format 指定默认pac 可向前兼容
        if not hasattr(args, 'format') and len(cfgs) == 1 and cfgs[0] == {}:
            cfgs[0]['format'] = 'pac'

        cfgs.extend(self.extra_jobs)
        for c in cfgs:
            cfg = self.default_opts.copy()
            cfg.update(c)
            check_deprecated_config(cfg.keys())
            job = Namespace.from_dict(
                dict([(k, v) for k, v in cfg.items() if k in opts]))
            for k, v in opts.items():
                dest, value = self.update_opt(args, cfg, k, **v)
                job.update(**{dest: value})
            job.user_rule.extend(self.extra_rules)
            self.jobs.append(job)

        self.jobs.sort(key=lambda j: j._order)

    def add_rule(self, rule):
        rule = rule.strip()
        if rule:
            self.extra_rules.append(rule)

    def add_job(self, job_cfgs):
        self.extra_jobs.append(job_cfgs)

    def clear_jobs(self):
        self.jobs = []

    def walk_jobs(self):
        for job in self.jobs:
            yield job

    def generate_all(self):
        for job in self.walk_jobs():
            self.generate(job)
            logger.debug('Job done: {0.format} => {0.output}'.format(job))

    def generate(self, job):
        if not job.format:
            raise FatalError('生成的格式不能为空, 请检查参数--format或配置format.')
        if job.format not in self._formaters:
            raise FatalError('发现不支持的生成格式: {}, 可选格式为: {}'.format(
                job.format, ', '.join(self._formaters.keys())))
        generator = Generator(job, self._formaters[job.format]['cls'])
        generator.generate()

    def run(self):
        self.parse_options()

        if self.init_dest:
            return self.init(self.init_dest)

        self.generate_all()

    def init(self, dest, force=False):
        try:
            path = abspath(dest)
            if not os.path.isdir(path):
                os.makedirs(path)
            config_dst = os.path.join(path, 'config.ini')
            user_rule_dst = os.path.join(path, 'user-rules.txt')
            exist = os.path.exists(config_dst) or os.path.exists(user_rule_dst)
            if not force and exist:
                raise FatalIOError('config file already exists.')
            with open_file(config_dst, 'w') as fp:
                fp.write(get_resource_data('res/tpl-config.ini'))
            with open_file(user_rule_dst, 'w') as fp:
                fp.write(get_resource_data('res/tpl-user-rules.txt'))
        except Exception as e:
            raise FatalError('初始化失败: {}'.format(e))


class Generator(object):
    # 在线获取的数据
    _cache = {}

    def __init__(self, options, formater_cls):
        super(Generator, self).__init__()
        self.options = copy.copy(options)
        self.formater = formater_cls(options=self.options, generator=self)

    def generate(self):
        if not self.formater.pre_generate():
            return

        user_rules = self.fetch_user_rules()
        gfwlist_rules, gfwlist_from, gfwlist_modified = self.fetch_gfwlist()
        self.formater._update_orginal_rules(user_rules, gfwlist_rules)

        modified, generated = self.std_datetime(gfwlist_modified)

        replacements = {'__VERSION__': __version__,
                        '__GENERATED__': generated,
                        '__MODIFIED__': modified,
                        '__GFWLIST_FROM__': gfwlist_from,
                        '__GENPAC__': 'genpac {} {}'.format(__version__,
                                                            __project_url__),
                        '__PROJECT_URL__': __project_url__,
                        '__GFWLIST_DETAIL__': '{} From {}'.format(
                            modified, gfwlist_from)}

        content = self.formater.generate(replacements)

        output = self.options.output
        if not output or output == '-':
            sys.stdout.write(content)
        else:
            write_file(output, content, fail_msg='写入输出文件`{path}`失败')

        self.formater.post_generate()

    def get_proxy(self):
        if not self.options.proxy:
            return

        _PROXY_TYPES['SOCKS'] = _PROXY_TYPES['SOCKS4']
        _PROXY_TYPES['PROXY'] = _PROXY_TYPES['HTTP']
        try:
            # format: [PROTOCOL://][USR:PWD]@HOST:PORT
            # protocol: http,socks4,socks5,socks
            matches = re.match(
                r'(?:(HTTP|SOCKS4|SOCKS5|SOCKS):\/\/)?(?:(.+):(.+)@)?(.+):(\d+)',
                self.options.proxy,
                re.IGNORECASE)
            type_, usr, pwd, host, port = matches.groups()
            type_ = (type_ or 'http').upper()
            logger.debug('PROXY TYPE: %s HOST: %s PORT: %d USR: %s PWD: %s', type_, host, int(port), usr, pwd)
            type_ = _PROXY_TYPES[type_] if type_ else _PROXY_TYPES['HTTP']
            return (type_, host, int(port), usr, pwd)
        except Exception as e:
            logger.error(e)
            raise FatalError('解析在线获取代理`{}`失败'.format(
                             self.options.proxy))

    def fetch_online(self, url):
        start = time.time()
        request = Request(url)
        proxy = self.get_proxy()
        if proxy:
            type_, host, port, usr, pwd = proxy
            socks.set_default_proxy(type_, host, int(port), username=usr, password=pwd)
            socket.socket = socks.socksocket
        response = urlopen(request)
        content = response.read()
        td = int((time.time() - start) * 1000)
        logger.debug('Fetch online done: {}ms {}'.format(td, url))
        return content.decode('utf-8')

    # 使用类变量缓存在线获取的内容
    def fetch(self, url):
        content = self.__class__._cache.get(url) or self.fetch_online(url)
        if content:
            self.__class__._cache[url] = content
        return content

    def fetch_gfwlist(self):
        if self.options.gfwlist_disabled:
            return [], '-', '-'

        content = ''
        gfwlist_from = '-'
        gfwlist_modified = '-'
        try:
            content = self.fetch(self.options.gfwlist_url)
            if not content:
                raise ValueError()
            gfwlist_from = 'online[{}]'.format(self.options.gfwlist_url)
            if self.options.gfwlist_local \
                    and self.options.gfwlist_update_local:
                write_file(self.options.gfwlist_local, content,
                           fail_msg='更新本地gfwlist文件{path}失败')
        except Exception as e:
            logger.error(e)
            if self.options.gfwlist_local:
                content = read_file(self.options.gfwlist_local,
                                    fail_msg='读取本地gfwlist文件{path}失败')
                gfwlist_from = 'local[{}]'.format(self.options.gfwlist_local)

        if not content:
            if self.options.gfwlist_url != '-' or self.options.gfwlist_local:
                raise FatalError(
                    '获取gfwlist失败. online: {} local: {}'.format(
                        self.options.gfwlist_url, self.options.gfwlist_local))
            else:
                gfwlist_from = '-'

        try:
            content = b64decode(content)
        except Exception:
            raise FatalError('解码gfwlist失败.')

        if self.options.gfwlist_decoded_save:
            write_file(self.options.gfwlist_decoded_save, content,
                       fail_msg='保存解码后的gfwlist到{path}失败: {error}')

        # 分行并去除第一行
        rules = content.splitlines()[1:]

        for line in rules:
            if line.startswith('! Last Modified:'):
                gfwlist_modified = line.split(':', 1)[1].strip()
                break

        return rules, gfwlist_from, gfwlist_modified

    def fetch_user_rules(self):
        rules = []
        rules.extend(self.options.user_rule)
        # for f in self.options.user_rule_from:
        #     content = read_file(f, fail_msg='读取自定义规则文件`{path}`失败')
        #     rules.extend(content.splitlines())
        # 支持目录
        rule_froms = []
        for f in self.options.user_rule_from:
            files = []
            if os.path.isdir(f):
                for sub_f in os.listdir(f):
                    if os.path.isfile(os.path.join(f, sub_f)):
                        rule_froms.append(os.path.join(f, sub_f))
            else:
                rule_froms.append(f)
        rule_froms.sort()
        for f in rule_froms:
            content = read_file(f, fail_msg='读取自定义规则文件`{path}`失败')
            rules.extend(content.splitlines())
        return rules

    def std_datetime(self, modified_datestr):
        def to_local(date_str):
            naive_date_str, _, offset_str = date_str.rpartition(' ')
            naive_dt = datetime.strptime(
                naive_date_str, '%a, %d %b %Y %H:%M:%S')
            offset = int(offset_str[-4:-2]) * 60 + int(offset_str[-2:])
            if offset_str[0] == "-":
                offset = -offset
            utc_date = naive_dt - timedelta(minutes=offset)

            ts = time.time()
            offset = datetime.fromtimestamp(ts) - \
                datetime.utcfromtimestamp(ts)
            return utc_date + offset

        try:
            modified = to_local(modified_datestr)
            return (modified.strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        except Exception:
            return (modified_datestr,
                    time.strftime('%a, %d %b %Y %H:%M:%S %z',
                                  time.localtime()))
    @classmethod
    def clear_cache(cls):
        logger.debug('Clear online data cache.')
        cls._cache.clear()


# 解析规则
# 参数 precise 影响返回格式
# precise = False 时 返回域名
# return: [忽略的域名, 被墙的域名]
#
# precise = True 时 返回 具体网址信息
# return: [忽略规则_正则表达式, 忽略规则_通配符, 被墙规则_正则表达式, 被墙规则_通配符]
def parse_rules(rules, precise=False):
    return _parse_rule_precise(rules) if precise else _parse_rule(rules)


def run():
    try:
        gp = GenPAC()
        gp.run()
    except Exception as e:
        exit_error(e)


# 普通解析
def _parse_rule(rules):
    direct_lst = []
    proxy_lst = []
    for line in rules:
        domain = ''

        # org_line = line

        if not line or line.startswith('!'):
            continue

        if line.startswith('@@'):
            line = line.lstrip('@|.')
            domain = surmise_domain(line)
            if domain:
                direct_lst.append(domain)
            continue
        elif line.find('.*') >= 0 or line.startswith('/'):
            line = line.replace('\/', '/').replace('\.', '.')  # noqa: W605
            try:
                m = re.search(r'([a-z0-9\.]+)\/.*', line)
                domain = surmise_domain(m.group(1))
                if domain:
                    proxy_lst.append(domain)
                continue
            except:
                pass
            try:
                m = re.search(r'([a-z0-9]+)\.\((.*)\)', line)
                m2 = re.split(r'[\(\)]', m.group(2))
                for tld in re.split(r'\|', m2[0]):
                    domain = surmise_domain('{}.{}'.format(m[1], tld))
                    if domain:
                        proxy_lst.append(domain)
                continue
            except:
                pass
            # logger.info('Parse rule fail: %s', org_line)
        elif line.startswith('|') or line.endswith('|'):
            line = line.strip('|')

        domain = surmise_domain(line)
        if domain:
            proxy_lst.append(domain)

    proxy_lst = list(set(proxy_lst))
    direct_lst = list(set(direct_lst))

    direct_lst = [d for d in direct_lst if d not in proxy_lst]

    proxy_lst.sort()
    direct_lst.sort()

    return [direct_lst, proxy_lst]


# 精确解析
def _parse_rule_precise(rules):
    def wildcard_to_regexp(pattern):
        pattern = re.sub(r'([\\\+\|\{\}\[\]\(\)\^\$\.\#])', r'\\\1',
                         pattern)
        # pattern = re.sub(r'\*+', r'*', pattern)
        pattern = re.sub(r'\*', r'.*', pattern)
        pattern = re.sub(r'\？', r'.', pattern)
        return pattern
    # d=direct p=proxy w=wildchar r=regexp
    result = {'d': {'w': [], 'r': []}, 'p': {'w': [], 'r': []}}
    for line in rules:
        line = line.strip()
        # comment
        if not line or line.startswith('!') or line.startswith('#'):
            continue
        d_or_p = 'p'
        w_or_r = 'r'
        # exception rules
        if line.startswith('@@'):
            line = line[2:]
            d_or_p = 'd'
        # regular expressions
        if line.startswith('/') and line.endswith('/'):
            line = line[1:-1]
        elif line.find('^') != -1:
            line = wildcard_to_regexp(line)
            line = re.sub(r'\\\^', r'(?:[^\w\-.%\u0080-\uFFFF]|$)', line)
        elif line.startswith('||'):
            line = wildcard_to_regexp(line[2:])
            # When using the constructor function, the normal string
            # escape rules (preceding special characters with \
            # in a string) are necessary.
            # when included For example, the following are equivalent:
            # re = new RegExp('\\w+')
            # re = /\w+/
            # via: http://aptana.com/reference/api/RegExp.html
            # line = r'^[\\w\\-]+:\\/+(?!\\/)(?:[^\\/]+\\.)?' + line
            # json.dumps will escape `\`
            line = r'^[\w\-]+:\/+(?!\/)(?:[^\/]+\.)?' + line
        elif line.startswith('|') or line.endswith('|'):
            line = wildcard_to_regexp(line)
            line = re.sub(r'^\\\|', '^', line, 1)
            line = re.sub(r'\\\|$', '$', line)
        else:
            w_or_r = 'w'
        if w_or_r == 'w':
            line = '*{}*'.format(line.strip('*'))
        result[d_or_p][w_or_r].append(line)

    return [result['d']['r'], result['d']['w'],
            result['p']['r'], result['p']['w']]
