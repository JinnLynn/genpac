# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import sys
import codecs
import argparse
import re
import base64
import json
import time
from datetime import datetime, timedelta
from urllib import unquote
from urllib2 import build_opener
from urlparse import urlparse
import itertools
import copy
from collections import OrderedDict
from base64 import b64decode
from pprint import pprint

from . import __version__
from .pysocks.socks import PROXY_TYPES as _proxy_types
from .pysocks.sockshandler import SocksiPyHandler
from .publicsuffix import PublicSuffixList
from .config import Config
from .deprecated import check_deprecated_args, check_deprecated_config

__all__ = ['gp']

GFWLIST_URL = \
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


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    if kwargs.get('exit', False):
        sys.exit(kwargs.get('exit_code', None) or 1)


def exit_error(*args, **kwargs):
    error(*args, exit=True, exit_code=kwargs.get('code') or 1)


def exit_success(*args):
    print(*args)
    sys.exit()


def abspath(path):
    if not path:
        return path
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


def open_file(path, mode='r'):
    path = abspath(path)
    return codecs.open(path, mode, 'utf-8')


def get_file_data(path):
    return open_file(path).read()


def open_resource(path, mode='r'):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    path = os.path.join(dir_path, path)
    return open_file(path, mode)


def get_resource_data(path):
    return open_resource(path).read()


def replace(text, adict):
    def one_xlat(match):
        return adict[match.group(0)]
    rx = re.compile('|'.join(map(re.escape, adict)))
    return rx.sub(one_xlat, text)


def local_datetime(date_str):
    naive_date_str, _, offset_str = date_str.rpartition(' ')
    naive_dt = datetime.strptime(naive_date_str, '%a, %d %b %Y %H:%M:%S')
    offset = int(offset_str[-4:-2])*60 + int(offset_str[-2:])
    if offset_str[0] == "-":
        offset = -offset
    utc_date = naive_dt - timedelta(minutes=offset)

    ts = time.time()
    offset = datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts)
    return utc_date + offset


def conv_bool(obj):
    if isinstance(obj, basestring):
        return True if obj.lower() == 'true' else False
    return bool(obj)


def conv_list(obj, sep=','):
    if obj is None:
        return []
    obj = obj if obj else []
    obj = obj if isinstance(obj, list) else [obj]
    if not sep:
        return obj
    return [s.strip() for s in sep.join(obj).split(sep) if s.strip()]


def conv_lower(obj):
    if obj is None:
        return ''
    if isinstance(obj, basestring):
        return obj.lower()
    return obj


class GenPAC(object):
    _formaters = {}

    _jobs = []
    _default_opts = {}

    def __init__(self):
        super(GenPAC, self).__init__()

    def check_formater(self):
        parser = self.build_args_parser()
        args, _ = parser.parse_known_args()
        fmt = getattr(args, 'format', None)
        if getattr(args, 'config_from', None):
            cfg = self.read_config(args.config_from)
            if 'format' in cfg:
                fmt = cfg['format']
        self.formater_name = fmt

    def formater(self, fmt, **options):
        def decorator(cls):
            self.add_formater(fmt, cls, **options)
            return cls
        return decorator

    def add_formater(self, fmt, cls, **options):
        # TODO: 检查cls是否合法
        cls._name = fmt
        self._formaters[fmt] = {'cls': cls,
                                'options': options}

    def walk_formaters(self, attr, *args, **kargs):
        for fmter in self._formaters.itervalues():
            getattr(fmter['cls'], attr)(*args, **kargs)

    def build_args_parser(self):
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
            '--format', choices=self._formaters.keys(),
            help='生成格式, 只有指定了格式, 相应格式的参数才作用')
        group.add_argument(
            '--gfwlist-url', metavar='URL',
            help='gfwlist网址，无此参数或URL为空则使用默认地址, URL为-则不在线获取')
        group.add_argument(
            '--gfwlist-proxy', metavar='PROXY',
            help='获取gfwlist时的代理, 如果可正常访问gfwlist地址, 则无必要使用该选项\n'
                 '格式为 "代理类型 [用户名:密码]@地址:端口" 其中用户名和密码可选, 如:\n'
                 '  SOCKS5 127.0.0.1:8080\n'
                 '  SOCKS5 username:password@127.0.0.1:8080\n')
        group.add_argument(
            '--gfwlist-local', metavar='FILE',
            help='本地gfwlist文件地址, 当在线地址获取失败时使用')
        group.add_argument(
            '--gfwlist-update-local', action='store_true',
            help='当在线gfwlist成功获取且--gfwlist-local参数存在时, '
                 '更新gfwlist-local内容')
        group.add_argument(
            '--gfwlist-disabled', action='store_true',
            help='禁用在线获取gfwlist')
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

        return parser

    def read_config(self, config_file):
        if not config_file:
            return [], {}
        try:
            with open_file(config_file) as fp:
                cfg_parser = Config()
                cfg_parser.parsefp(fp)
                return (cfg_parser.options('config', True),
                        cfg_parser.options('default'))
        except:
            exit_error('配置文件读取失败')

    def update_opt(self, args, cfgs, key,
                   default=None, conv=None, dest=None, **kwargs):
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

        if isinstance(v, basestring):
            v = v.strip(' \'\t"')

        if conv:
            v = conv(v)

        return dest, v

    def parse_options(self):
        # 检查弃用参数 警告
        check_deprecated_args()

        parser = self.build_args_parser()
        self.walk_formaters('arguments', parser)
        args = parser.parse_args()

        if args.init:
            self.init(args.init)

        cfgs, self._default_opts = self.read_config(args.config_from)
        self._jobs = []

        opts = {}
        opts['format'] = {'conv': conv_lower}

        opts['gfwlist-url'] = {'default': GFWLIST_URL}
        opts['gfwlist-proxy'] = {}
        opts['gfwlist-local'] = {}
        opts['gfwlist-disabled'] = {'conv': conv_bool}
        opts['gfwlist-update-local'] = {'conv': conv_bool}
        opts['user-rule-from'] = {}
        opts['output'] = {}

        opts['user-rule'] = {'conv': conv_list}
        opts['user-rule-from'] = {'conv': conv_list}

        self.walk_formaters('config', opts)

        if not cfgs:
            cfgs = [{}]

        for c in cfgs:
            cfg = self._default_opts.copy()
            cfg.update(c)
            check_deprecated_config(cfg.keys())
            job = Namespace.from_dict(
                dict([(k, v) for k, v in cfg.iteritems() if k in opts]))
            for k, v in opts.iteritems():
                dest, value = self.update_opt(args, cfg, k, **v)
                job.update(**{dest: value})
            self._jobs.append(job)

    def init(self, dest):
        try:
            path = abspath(dest if isinstance(dest, basestring) else '.')
            if not os.path.isdir(path):
                os.makedirs(path)
            config_dst = os.path.join(path, 'config.ini')
            user_rule_dst = os.path.join(path, 'user-rules.txt')
            if os.path.exists(config_dst) or os.path.exists(user_rule_dst):
                ans = raw_input('文件已存在, 是否覆盖?[y|n]: '.encode('utf-8'))
                if ans.lower() != 'y':
                    raise Exception('文件已存在')
            with open_file(config_dst, 'w') as fp:
                fp.write(get_resource_data('res/config-sample.ini'))
            with open_file(user_rule_dst, 'w') as fp:
                fp.write(get_resource_data('res/user-rules-sample.txt'))
        except Exception as e:
            exit_error('初始化失败: {}'.format(e))
        exit_success('已成功初始化')

    def walk_jobs(self):
        for job in self._jobs:
            yield job

    def run(self):
        self.parse_options()

        for job in self.walk_jobs():
            self.generate(job)

    def generate(self, job):
        if not job.format:
            exit_error('生成的格式不能为空, 请检查参数--format或配置format.')
        if job.format not in self._formaters:
            exit_error('发现不支持的生成格式: {}, 可选格式为: {}'.format(
                job.format, ', '.join(self._formaters.keys())))
        print('-')
        pprint(job)
        generator = Generator(job, self._formaters[job.format]['cls'])
        generator.generate()


class Generator(object):
    def __init__(self, options, formater_cls):
        super(Generator, self).__init__()
        self.options = copy.copy(options)
        self.formater = formater_cls(options=self.options)

    def generate(self):
        if not self.formater.pre_generate():
            return

        gfwlist_rules, gfwlist_from, gfwlist_modified = self.fetch_gfwlist()
        user_rules = self.fetch_user_rules()

        try:
            new_date = local_datetime(gfwlist_modified)
            gfwlist_modified = new_date.strftime('%Y-%m-%d %H:%M:%S')
            generated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            generated = time.strftime('%a, %d %b %Y %H:%M:%S %z',
                                      time.localtime())

        replacements = {'__VERSION__': __version__,
                        '__GENERATED__': generated,
                        '__MODIFIED__': gfwlist_modified,
                        '__GFWLIST_FROM__': gfwlist_from}

        content = self.formater.generate(
            gfwlist_rules, user_rules, replacements)

        output = self.options.output
        if not output or output == '-':
            return sys.stdout.write(content)
        try:
            with open_file(output, 'w') as fp:
                fp.write(content)
        except Exception:
            exit_error('写入输出文件`{}`失败'.format(output))

        self.formater.post_generate()

    def init_opener(self):
        if not self.options.gfwlist_proxy:
            return build_opener()
        _proxy_types['SOCKS'] = _proxy_types['SOCKS4']
        _proxy_types['PROXY'] = _proxy_types['HTTP']
        try:
            # format: PROXY|SOCKS|SOCKS4|SOCKS5 [USR:PWD]@HOST:PORT
            matches = re.match(
                r'(PROXY|SOCKS|SOCKS4|SOCKS5) (?:(.+):(.+)@)?(.+):(\d+)',
                self.options.gfwlist_proxy,
                re.IGNORECASE)
            type_, usr, pwd, host, port = matches.groups()
            type_ = _proxy_types[type_.upper()]
            return build_opener(
                SocksiPyHandler(type_, host, int(port),
                                username=usr, password=pwd))
        except:
            exit_error('解析获取gfwlist的代理`{}`失败'.format(
                self.options.gfwlist_proxy))

    def fetch_gfwlist(self):
        if self.options.gfwlist_disabled:
            return [], '-', '-'

        content = ''
        gfwlist_from = '-'
        gfwlist_modified = '-'
        try:
            opener = self.init_opener()
            res = opener.open(self.options.gfwlist_url)
            content = res.read()
        except:
            try:
                with open_file(self.options.gfwlist_local) as fp:
                    content = fp.read()
                gfwlist_from = 'local[{}]'.format(self.options.gfwlist_local)
            except:
                pass
        else:
            gfwlist_from = 'online[{}]'.format(self.options.gfwlist_url)
            if self.options.gfwlist_local \
                    and self.options.gfwlist_update_local:
                with open_file(self.options.gfwlist_local, 'w') as fp:
                    fp.write(content)

        if not content:
            if self.options.gfwlist_url != '-' or self.options.gfwlist_local:
                exit_error('获取gfwlist失败. online: {} local: {}'.format(
                    self.options.gfwlist_url, self.options.gfwlist_local))
            else:
                gfwlist_from = '-'

        try:
            content = '! {}'.format(base64.decodestring(content))
        except:
            exit_error('解码gfwlist失败.')

        content = content.splitlines()
        for line in content:
            if line.startswith('! Last Modified:'):
                gfwlist_modified = line.split(':', 1)[1].strip()
                break

        return content, gfwlist_from, gfwlist_modified

    def fetch_user_rules(self):
        rules = self.options.user_rule
        for f in self.options.user_rule_from:
            if not f:
                continue
            try:
                with open_file(f) as fp:
                    file_rules = fp.read().splitlines()
                    rules.extend(file_rules)
            except:
                exit_error('读取自定义规则文件`{}`失败'.format(f))
        return rules


gp = GenPAC()


class FmtBase(object):
    _psl = None
    _name = ''

    def __init__(self, *args, **kwargs):
        super(FmtBase, self).__init__()
        self.options = kwargs.get('options') or Namespace()

    @classmethod
    def arguments(cls, parser):
        pass

    @classmethod
    def config(cls, options):
        pass

    @property
    def tpl(self):
        return ''

    def pre_generate(self):
        return True

    def generate(self, gfwlist_rules, user_rules, replacements):
        pass

    def post_generate(self):
        pass

    def error(self, msg):
        error('{}格式生成错误: {}'.format(self._name.upper(), msg))

    # 普通解析，仅匹配域名
    # 返回格式：[直接访问, 代理访问]
    def parse_rules(self, rules):
        direct_lst = []
        proxy_lst = []
        for line in rules:
            domain = ''

            if not line or line.startswith('!'):
                continue

            if line.startswith('@@'):
                line = line.lstrip('@|.')
                domain = self._surmise_domain(line)
                if domain:
                    direct_lst.append(domain)
                continue
            elif line.find('.*') >= 0 or line.startswith('/'):
                line = line.replace('\/', '/').replace('\.', '.')
                try:
                    m = re.search(r'[a-z0-9]+\..*', line)
                    domain = self._surmise_domain(m.group(0))
                    if domain:
                        proxy_lst.append(domain)
                        continue
                    m = re.search(r'[a-z]+\.\(.*\)', line)
                    m2 = re.split(r'[\(\)]', m.group(0))
                    for tld in re.split(r'\|', m2[1]):
                        domain = self._surmise_domain(
                            '{}{}'.format(m2[0], tld))
                        if domain:
                            proxy_lst.append(domain)
                except:
                    pass
                continue
            elif line.startswith('|'):
                line = line.lstrip('|')
            domain = self._surmise_domain(line)
            if domain:
                proxy_lst.append(domain)

        proxy_lst = list(set(proxy_lst))
        direct_lst = list(set(direct_lst))

        direct_lst = [d for d in direct_lst if d not in proxy_lst]

        proxy_lst.sort()
        direct_lst.sort()

        return [direct_lst, proxy_lst]

    # 精确解析, 匹配具体网址
    # 返回格式为:
    #  [直接访问_正则表达式, 直接访问_通配符, 代理访问_正则表达式, 代理访问_通配符]
    def parse_rules_precise(self, rules):
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
            if not line or line.startswith('!'):
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

    def _surmise_domain(self, rule):
        domain = ''

        rule = self._clear_asterisk(rule)
        rule = rule.lstrip('.')

        if rule.find('%2F') >= 0:
            rule = unquote(rule)

        if rule.startswith('http:') or rule.startswith('https:'):
            r = urlparse(rule)
            domain = r.hostname
        elif rule.find('/') > 0:
            r = urlparse('http://' + rule)
            domain = r.hostname
        elif rule.find('.') > 0:
            domain = rule

        return self._get_public_suffix(domain)

    def _get_public_suffix(self, host):
        if not self._psl:
            self._psl = PublicSuffixList(
                open_resource('res/public_suffix_list.dat'))
        domain = self._psl.get_public_suffix(host)
        return None if domain.find('.') < 0 else domain

    def _clear_asterisk(self, rule):
        if rule.find('*') < 0:
            return rule
        rule = rule.strip('*')
        rule = rule.replace('/*.', '/')
        rule = re.sub(r'/([a-zA-Z0-9]+)\*\.', '/', rule)
        rule = re.sub(r'\*([a-zA-Z0-9_%]+)', '', rule)
        rule = re.sub(r'^([a-zA-Z0-9_%]+)\*', '', rule)
        return rule


@gp.formater('pac')
class FmtPAC(FmtBase):
    def __init__(self, *args, **kwargs):
        super(FmtPAC, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = parser.add_argument_group(
            title=cls._name.upper(),
            description='通过代理自动配置文件（PAC）系统或浏览器可自动选择合适的'
                        '代理服务器')
        group.add_argument(
            '--pac-proxy', metavar='PROXY',
            help='代理地址, 如 SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080')
        group.add_argument(
            '--pac-precise', action='store_true',
            help='精确匹配模式')
        group.add_argument(
            '--pac-compress', action='store_true',
            help='压缩输出')

        # 弃用的参数
        group.add_argument(
            '-p', '--proxy', dest='pac_proxy',  metavar='PROXY',
            help='已弃用参数, 等同于--pac-proxy, 后续版本将删除, 避免使用')
        group.add_argument(
            '-P', '--precise', action='store_true',
            dest='pac_precise',
            help='已弃用参数, 等同于--pac-precise, 后续版本将删除, 避免使用')
        group.add_argument(
            '-z', '--compress', action='store_true',
            dest='pac_compress',
            help='已弃用参数, 等同于--pac-compress, 后续版本将删除, 避免使用')


    @classmethod
    def config(cls, options):
        options['pac-proxy'] = {'replaced': 'proxy'}
        options['pac-compress'] = {'conv': conv_bool, 'replaced': 'compress'}
        options['pac-precise'] = {'conv': conv_bool, 'replaced': 'precise'}

    @property
    def tpl(self):
        pac_tpl = 'res/tpl-pac-precise.js' if self.options.pac_precise else \
            'res/tpl-pac.js'
        if self.options.pac_compress:
            pac_tpl = pac_tpl.split('.')
            pac_tpl.insert(-1, 'min')
            pac_tpl = '.'.join(pac_tpl)
        return get_resource_data(pac_tpl)

    def pre_generate(self):
        if not self.options.pac_proxy:
            self.error('代理信息不存在，检查参数--pac-proxy或配置pac-proxy')
            return False
        return super(FmtPAC, self).pre_generate()

    def generate(self, gfwlist_rules, user_rules, replacements):
        func_parse = self.parse_rules_precise if self.options.pac_precise \
            else self.parse_rules
        rules = [func_parse(user_rules), func_parse(gfwlist_rules)]

        rules = json.dumps(
            rules,
            indent=None if self.options.pac_compress else 4,
            separators=(',', ':') if self.options.pac_compress else None)
        replacements.update({'__PROXY__': self.options.pac_proxy,
                             '__RULES__': rules})
        return replace(self.tpl, replacements)


@gp.formater('dnsmasq')
class FmtDnsmasq(FmtBase):
    _default_dns = '127.0.0.1#53'
    _default_ipset = 'GFWLIST'

    def __init__(self, *args, **kwargs):
        super(FmtDnsmasq, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = parser.add_argument_group(
            title=cls._name.upper(),
            description='Dnsmasq配合iptables ipset可实现基于域名的自动直连或代理')
        group.add_argument(
            '--dnsmasq-dns', metavar='DNS',
            help='生成规则域名查询使用的DNS服务器，格式: HOST#PORT\n'
                 '默认: {}'.format(cls._default_dns))
        group.add_argument(
            '--dnsmasq-ipset', metavar='IPSET',
            help='转发使用的ipset名称, 默认: {}'.format(cls._default_ipset))

    @classmethod
    def config(cls, options):
        options['dnsmasq-dns'] = {'default': cls._default_dns}
        options['dnsmasq-ipset'] = {'default': cls._default_ipset}

    @property
    def tpl(self):
        return get_resource_data('res/tpl-dnsmasq.ini')

    def generate(self, gfwlist_rules, user_rules, replacements):
        rules = [self.parse_rules(user_rules),
                 self.parse_rules(gfwlist_rules)]
        dns = self.options.dnsmasq_dns
        ipset = self.options.dnsmasq_ipset
        # 不需要忽略的domain
        rules = list(set(rules[0][1] + rules[1][1]))
        rules.sort()
        servers = ['server=/{}/{}'.format(s, dns) for s in rules]
        ipsets = ['ipset=/{}/{}'.format(s, ipset) for s in rules]
        merged_lst = list(itertools.chain.from_iterable(zip(servers, ipsets)))

        replacements.update({'__DNSMASQ__': '\n'.join(merged_lst).strip()})
        return replace(self.tpl, replacements)


@gp.formater('wingy')
class FmtWingy(FmtBase):
    def __init__(self, *args, **kwargs):
        super(FmtWingy, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = parser.add_argument_group(
            title=cls._name.upper(),
            description='Wingy是iOS下基于NEKit的代理App')
        group.add_argument(
            '--wingy-adapter-opts', metavar='OPTS',
            help='adapter选项, 选项间使用`,`分割, 多个adapter使用`;`分割, 如:\n'
                 '  id:ap1,type:http,host:127.0.0.1,port:8080;'
                 'id:ap2,type:socks5,host:127.0.0.1,port:3128')
        group.add_argument(
            '--wingy-rule-adapter-id', metavar='ID',
            help='生成规则使用的adapter ID')
        group.add_argument(
            '--wingy-template', metavar='FILE',
            help='自定义模板文件')

    @classmethod
    def config(cls, options):
        options['wingy-adapter-opts'] = {}
        options['wingy-rule-adapter-id'] = {}
        options['wingy-template'] = {}

    @property
    def tpl(self):
        if not self.options.wingy_template:
            return get_resource_data('res/tpl-wingy.yaml')
        return get_file_data(self.options.wingy_template)

    def generate(self, gfwlist_rules, user_rules, replacements):
        rules = [self.parse_rules(user_rules),
                 self.parse_rules(gfwlist_rules)]
        # 不需要忽略的domain
        rules = list(set(rules[0][1] + rules[1][1]))
        rules.sort()
        fmt = '{:>8}'.format(' ')
        domains = ['{}- s,{}'.format(fmt, s) for s in rules]

        # adapter
        adapter = self._parse_adapter()

        replacements.update({
            '__ADAPTER__': adapter,
            '__RULE_ADAPTER_ID__': self.options.wingy_rule_adapter_id,
            '__CRITERIA__': '\n'.join(domains),
            })
        return replace(self.tpl, replacements)

    def _parse_adapter(self):
        def split(txt, sep):
            return [s.strip() for s in txt.split(sep) if s.strip()]

        def to_yaml(opts):
            tmp = []
            for k, v in opts.iteritems():
                tmp.append('{:>6}{}: {}'.format('', k, v))
            tmp[0] = '{:>4}- {}'.format('', tmp[0].strip())
            return '\n'.join(tmp)

        def ss_uri(aid, uri):
            encoded = uri.lstrip('ss://').lstrip('//').rstrip('=') + '=='
            decoded = b64decode(encoded)
            auth = False
            method, pwd_host, port = decoded.split(':')
            pwd, host = pwd_host.split('@')
            if method.endswith('-auth'):
                auth = True
                method = method.rstrip('-auth')
            opts = OrderedDict([('id', aid), ('type', 'ss')])
            opts.setdefault('host', host)
            opts.setdefault('port', port)
            opts.setdefault('method', method)
            opts.setdefault('password', pwd)
            if auth:
                opts.setdefault('protocol', 'verify_sha1')
            return opts

        adapter_opts = self.options.wingy_adapter_opts
        if not adapter_opts:
            return
        opts = []
        for opt in split(adapter_opts, ';'):
            k_v = split(opt, ',')
            od = OrderedDict()
            map(lambda x: od.setdefault(x.split(':')[0], x.split(':')[1]),
                k_v)
            if 'ss' in od:
                od = ss_uri(od['id'], od['ss'])
            opts.append(to_yaml(od))
        return '\n'.join(opts)
