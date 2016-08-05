# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import
import os
import sys
import argparse
import codecs
from ConfigParser import ConfigParser
import urllib2
import re
import base64
import json
import time
import urlparse
import urllib
import pkgutil

from .pysocks.socks import PROXY_TYPES as _proxy_types
from .pysocks.sockshandler import SocksiPyHandler
from .publicsuffix import PublicSuffixList

__version__ = '1.4.1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2016 JinnLynn'

__all__ = ['main']

GFWLIST_URL = \
    'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'

_cfg = None
_psl = None


def abspath(path):
    if not path:
        return path
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


def resource_data(path):
    return pkgutil.get_data('genpac', path)


def resource_stream(path, mode='r'):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    path = os.path.join(dir_path, path)
    return codecs.open(path, mode, 'utf-8')


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    if kwargs.get('exit', False):
        sys.exit(1)


def replace(content, replaces):
    for k, v in replaces.items():
        content = content.replace(k, v)
    return content


def build_args_parser():
    # 如果某选项同时可以在配置文件和命令行中设定，则必须使default=None
    # 以避免命令行中即使没指定该参数，也会覆盖配置文件中的值
    # 原因见parse_config() -> update(name, key, default=None)
    parser = argparse.ArgumentParser(prog='genpac', add_help=False)
    parser.add_argument('-p', '--proxy')
    parser.add_argument('--gfwlist-url', default=None)
    parser.add_argument('--gfwlist-proxy')
    parser.add_argument('--gfwlist-local')
    parser.add_argument('--update-gfwlist-local', action='store_true',
                        default=None)
    parser.add_argument('--gfwlist-disabled', action='store_true',
                        default=None)
    parser.add_argument('--user-rule', action='append')
    parser.add_argument('--user-rule-from', action='append')
    parser.add_argument('-P', '--precise', action='store_true', default=None)
    parser.add_argument('-o', '--output')
    parser.add_argument('-c', '--config-from')
    parser.add_argument('-z', '--compress', action='store_true', default=None)
    parser.add_argument('--init', nargs='?', const=True, default=False)
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    parser.add_argument('-h', '--help', action='store_true')
    return parser


def parse_config(parser=None):
    cfg = {}
    if not parser:
        parser = build_args_parser()
    args = parser.parse_args()

    def update(name, key, default=None):
        v = getattr(args, name, None)
        if v is not None:
            return v
        try:
            return cfg.get(key, default).strip(' \'\t"')
        except:
            return default

    def conv_bool(obj):
        if isinstance(obj, basestring):
            return True if obj.lower() == 'true' else False
        return bool(obj)

    def list_v(obj, sep=','):
        obj = obj if obj else []
        obj = obj if isinstance(obj, list) else [obj]
        if not sep:
            return obj
        return [s.strip() for s in sep.join(obj).split(sep) if s.strip()]

    if args.config_from:
        try:
            with codecs.open(abspath(args.config_from), 'r', 'utf-8') as fp:
                cfg_parser = ConfigParser()
                cfg_parser.readfp(fp)
                cfg = dict(cfg_parser.items('config'))

            args.gfwlist_url = update('gfwlist_url', 'gfwlist-url',
                                      GFWLIST_URL)
            args.gfwlist_proxy = update('gfwlist_proxy', 'gfwlist-proxy')
            args.gfwlist_local = update('gfwlist_local', 'gfwlist-local')
            args.gfwlist_disabled = conv_bool(
                update('gfwlist_disabled', 'gfwlist-disabled', False))
            args.update_gfwlist_local = conv_bool(
                update('update_gfwlist_local', 'update-gfwlist-local', False))
            args.proxy = update('proxy', 'proxy')
            args.user_rule_from = update('user_rule_from', 'user-rule-from')
            args.output = update('output', 'output')
            args.compress = conv_bool(update('compress', 'compress', False))
            args.precise = conv_bool(update('precise', 'precise', False))
        except:
            error('read config file fail.', exit=True)
    args.user_rule = list_v(args.user_rule)
    args.user_rule_from = list_v(args.user_rule_from)
    if not args.gfwlist_url:
        args.gfwlist_url = GFWLIST_URL
    return args


def init():
    try:
        path = abspath(_cfg.init if isinstance(_cfg.init, basestring) else '.')
        if not os.path.isdir(path):
            os.makedirs(path)
        config_dst = os.path.join(path, 'config.ini')
        user_rule_dst = os.path.join(path, 'user-rules.txt')
        if os.path.exists(config_dst) or os.path.exists(user_rule_dst):
            ans = raw_input('file already exists, overwrite?[y|n]: ')
            if ans.lower() != 'y':
                raise Exception('file already exists.')
        with open(config_dst, 'w') as fp:
            fp.write(resource_data('res/config-sample.ini'))
        with open(user_rule_dst, 'w') as fp:
            fp.write(resource_data('res/user-rules-sample.txt'))
    except Exception as e:
        error('init fail: {}'.format(e), exit=True)
    print('init success.')
    sys.exit()


def print_help():
    print('genpac {}'.format(__version__))
    print('-----')
    print(resource_data('res/help.txt'))
    sys.exit()


def build_opener():
    if not _cfg.gfwlist_proxy:
        return urllib2.build_opener()
    _proxy_types['SOCKS'] = _proxy_types['SOCKS4']
    _proxy_types['PROXY'] = _proxy_types['HTTP']
    try:
        # format: PROXY|SOCKS|SOCKS4|SOCKS5 [USR:PWD]@HOST:PORT
        matches = re.match(
            r'(PROXY|SOCKS|SOCKS4|SOCKS5) (?:(.+):(.+)@)?(.+):(\d+)',
            _cfg.gfwlist_proxy,
            re.IGNORECASE)
        type_, usr, pwd, host, port = matches.groups()
        type_ = _proxy_types[type_.upper()]
        return urllib2.build_opener(
            SocksiPyHandler(type_, host, int(port),
                            username=usr, password=pwd))
    except:
        error('gfwlist proxy \'{}\' error. '.format(_cfg.gfwlist_proxy),
              exit=True)


def fetch_gfwlist():
    if _cfg.gfwlist_disabled:
        return [], '-', '-'

    content = ''
    gfwlist_from = '-'
    gfwlist_modified = '-'
    try:
        opener = build_opener()
        res = opener.open(_cfg.gfwlist_url)
        content = res.read()
    except:
        try:
            with codecs.open(abspath(_cfg.gfwlist_local), 'r', 'utf-8') as fp:
                content = fp.read()
            gfwlist_from = 'local[{}]'.format(_cfg.gfwlist_local)
        except:
            pass
    else:
        gfwlist_from = 'online[{}]'.format(_cfg.gfwlist_url)
        if _cfg.gfwlist_local and _cfg.update_gfwlist_local:
            with codecs.open(abspath(_cfg.gfwlist_local), 'w', 'utf-8') as fp:
                fp.write(content)

    if not content:
        if _cfg.gfwlist_url != '-' or _cfg.gfwlist_local:
            error('fetch gfwlist fail. online: {} local: {}'.format(
                    _cfg.gfwlist_url, _cfg.gfwlist_local), exit=True)
        else:
            gfwlist_from = '-'

    try:
        content = '! {}'.format(base64.decodestring(content))
    except:
        error('base64 decode fail.', exit=True)

    content = content.splitlines()
    for line in content:
        if line.startswith('! Last Modified:'):
            gfwlist_modified = line.split(':', 1)[1].strip()
            break

    return content, gfwlist_from, gfwlist_modified


def fetch_user_rules():
    rules = _cfg.user_rule
    for f in _cfg.user_rule_from:
        if not f:
            continue
        try:
            with codecs.open(abspath(f), 'r', 'utf-8') as fp:
                file_rules = fp.read().splitlines()
                rules.extend(file_rules)
        except:
            error('read user rule file fail. ', f, exit=True)
    return rules


def parse_rules_precise(rules):
    def wildcard_to_regexp(pattern):
        pattern = re.sub(r'([\\\+\|\{\}\[\]\(\)\^\$\.\#])', r'\\\1', pattern)
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
            # escape rules (preceding special characters with \ when included
            # in a string) are necessary.
            # For example, the following are equivalent:
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


def get_public_suffix(host):
    global _psl
    if not _psl:
        _psl = PublicSuffixList(resource_stream('res/public_suffix_list.dat'))
    domain = _psl.get_public_suffix(host)
    return None if domain.find('.') < 0 else domain


def surmise_domain(rule):
    domain = ''

    rule = clear_asterisk(rule)
    rule = rule.lstrip('.')

    if rule.find('%2F') >= 0:
        rule = urllib.unquote(rule)

    if rule.startswith('http:') or rule.startswith('https:'):
        r = urlparse.urlparse(rule)
        domain = r.hostname
    elif rule.find('/') > 0:
        r = urlparse.urlparse('http://' + rule)
        domain = r.hostname
    elif rule.find('.') > 0:
        domain = rule

    return get_public_suffix(domain)


def clear_asterisk(rule):
    if rule.find('*') < 0:
        return rule
    rule = rule.strip('*')
    rule = rule.replace('/*.', '/')
    rule = re.sub(r'/([a-zA-Z0-9]+)\*\.', '/', rule)
    rule = re.sub(r'\*([a-zA-Z0-9_%]+)', '', rule)
    rule = re.sub(r'^([a-zA-Z0-9_%]+)\*', '', rule)
    return rule


def parse_rules(rules):
    direct_lst = []
    proxy_lst = []
    for line in rules:
        domain = ''

        if not line or line.startswith('!'):
            continue

        if line.startswith('@@'):
            line = line.lstrip('@|.')
            domain = surmise_domain(line)
            if domain:
                direct_lst.append(domain)
            continue
        elif line.find('.*') >= 0 or line.startswith('/'):
            line = line.replace('\/', '/').replace('\.', '.')
            try:
                m = re.search(r'[a-z0-9]+\..*', line)
                domain = surmise_domain(m.group(0))
                if domain:
                    proxy_lst.append(domain)
                    continue
                m = re.search(r'[a-z]+\.\(.*\)', line)
                m2 = re.split(r'[\(\)]', m.group(0))
                for tld in re.split(r'\|', m2[1]):
                    domain = surmise_domain('{}{}'.format(m2[0], tld))
                    if domain:
                        proxy_lst.append(domain)
            except:
                pass
            continue
        elif line.startswith('|'):
            line = line.lstrip('|')
        domain = surmise_domain(line)
        if domain:
            proxy_lst.append(domain)

    proxy_lst = list(set(proxy_lst))
    direct_lst = list(set(direct_lst))

    direct_lst = [d for d in direct_lst if d not in proxy_lst]

    proxy_lst.sort()
    direct_lst.sort()

    return [direct_lst, proxy_lst]


def get_pac_tpl():
    pac_tpl = 'res/pac-tpl-precise.js' if _cfg.precise else 'res/pac-tpl.js'
    if _cfg.compress:
        pac_tpl = pac_tpl.split('.')
        pac_tpl.insert(-1, 'min')
        pac_tpl = '.'.join(pac_tpl)
    return resource_data(pac_tpl)


def generate():
    if not _cfg.proxy:
        error('PAC requires a proxy value, SEE option --proxy.', exit=True)

    gfwlist_rules, gfwlist_from, gfwlist_modified = fetch_gfwlist()
    user_rules = fetch_user_rules()

    func_parse = parse_rules_precise if _cfg.precise else parse_rules
    rules = [func_parse(user_rules), func_parse(gfwlist_rules)]

    rules = json.dumps(rules,
                       indent=None if _cfg.compress else 4,
                       separators=(',', ':') if _cfg.compress else None)
    generated = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime())
    content = get_pac_tpl()
    content = replace(content, {'__VERSION__': __version__,
                                '__GENERATED__': generated,
                                '__MODIFIED__': gfwlist_modified,
                                '__GFWLIST_FROM__': gfwlist_from,
                                '__PROXY__': _cfg.proxy,
                                '__RULES__': rules})

    if not _cfg.output or _cfg.output == '-':
        return sys.stdout.write(content)
    try:
        with codecs.open(abspath(_cfg.output), 'w', 'utf-8') as fp:
            fp.write(content)
    except Exception:
        error('write output file fail. {}'.format(_cfg.output), exit=True)


def main():
    global _cfg
    _cfg = parse_config()

    if _cfg.help:
        print_help()
    elif _cfg.init:
        init()
    else:
        generate()


if __name__ == '__main__':
    main()
