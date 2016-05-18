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
import shutil
import urlparse
import urllib
import pkgutil

from .pysocks.socks import PROXY_TYPES as _proxy_types
from .pysocks.sockshandler import SocksiPyHandler
from .publicsuffix import PublicSuffixList

__version__ = '1.3.1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2015 JinnLynn'

__all__ = ['main']

_default_url = \
    'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'
_proxy_types['SOCKS'] = _proxy_types['SOCKS4']
_proxy_types['PROXY'] = _proxy_types['HTTP']

_help_tpl = 'res/help.txt'
_pac_tpl = 'res/pac-tpl.js'
_pac_tpl_precise = 'res/pac-tpl-precise.js'
_config_sample = 'res/config-sample.ini'
_user_rule_sample = 'res/user-rules-sample.txt'
_public_suffix_list = 'res/public_suffix_list.dat'

_cfg = None
_psl = None
_gfwlist_from = '-'
_gfwlist_modified = '-'
_org_rule = ''


def _write(f, content):
    if isinstance(content, list):
        content = '\n'.join(content)
    with open(f, 'w') as fp:
        fp.write(content)


class HelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super(HelpAction, self).__init__(option_strings, dest, nargs=0,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(resource_data(_help_tpl))
        parser.exit()


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


def parse_args():
    parser = argparse.ArgumentParser(prog='genpac', add_help=False)
    parser.add_argument('-p', '--proxy')
    parser.add_argument('--gfwlist-url', default=None)
    parser.add_argument('--gfwlist-proxy')
    parser.add_argument('--gfwlist-local')
    parser.add_argument('--update-gfwlist-local', action='store_true')
    parser.add_argument('--gfwlist-disabled', action='store_true',
                        default=None)
    parser.add_argument('--user-rule', action='append')
    parser.add_argument('--user-rule-from', action='append')
    parser.add_argument('--precise', action='store_true', default=None)
    parser.add_argument('-o', '--output')
    parser.add_argument('-c', '--config-from')
    parser.add_argument('-z', '--compress', action='store_true', default=None)
    parser.add_argument('--init', nargs='?', const=True, default=False)
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    parser.add_argument('-h', '--help', action=HelpAction)
    return parser.parse_args()


def parse_config():
    cfg = {}
    args = parse_args()

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
                                      _default_url)
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
            if not args.gfwlist_url:
                args.gfwlist_url = _default_url
        except:
            error('read config file fail.', exit=True)
    args.user_rule = list_v(args.user_rule)
    args.user_rule_from = list_v(args.user_rule_from)
    return args


def prepare():
    global _cfg
    _cfg = parse_config()
    _cfg.output = _cfg.output
    _cfg.gfwlist_local = _cfg.gfwlist_local

    init_sample()


def init_sample():
    if not _cfg.init:
        return
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
            fp.write(resource_data(_config_sample))
        with open(user_rule_dst, 'w') as fp:
            fp.write(resource_data(_user_rule_sample))
    except Exception as e:
        error('init fail: {}'.format(e), exit=True)
    print('init success.')
    sys.exit()


def build_opener():
    if not _cfg.gfwlist_proxy:
        return urllib2.build_opener()
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
    global _gfwlist_from, _gfwlist_modified
    if _cfg.gfwlist_disabled:
        return ''

    content = ''
    try:
        opener = build_opener()
        res = opener.open(_cfg.gfwlist_url)
        content = res.read()
    except:
        try:
            with codecs.open(abspath(_cfg.gfwlist_local), 'r', 'utf-8') as fp:
                content = fp.read()
            _gfwlist_from = 'local[{}]'.format(_cfg.gfwlist_local)
        except:
            pass
    else:
        _gfwlist_from = 'online[{}]'.format(_cfg.gfwlist_url)
        if _cfg.gfwlist_local and _cfg.update_gfwlist_local:
            with codecs.open(abspath(_cfg.gfwlist_local), 'w', 'utf-8') as fp:
                fp.write(content)

    if not content:
        if _cfg.gfwlist_url != '-' or _cfg.gfwlist_local:
            error('fetch gfwlist fail.', exit=True)
        else:
            _gfwlist_from = '-'

    try:
        content = '! {}'.format(base64.decodestring(content))
        content = content.splitlines()
        for line in content:
            if line.startswith('!') and 'Last Modified' in line:
                _gfwlist_modified = line.split(':', 1)[1].strip()
                break
        else:
            _gfwlist_modified = '-'
    except:
        pass

    return content


def fetch_user_rules():
    rules = _cfg.user_rule
    for f in _cfg.user_rule_from:
        if not f:
            continue
        try:
            with codecs.open(abspath(f), 'r', 'utf-8') as fp:
                file_rules = fp.read().split('\n')
                rules.extend(file_rules)
        except:
            error('read user rule file fail. ', f)
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


def surmise_domain(rule):
    global _psl
    if not _psl:
        _psl = PublicSuffixList(resource_stream(_public_suffix_list))

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

    domain = _psl.get_public_suffix(domain)
    if domain.find('.') < 0:
        domain = None
    # if not domain:
    #     print('{:<30.30} => {:<30.30} => {}'.format(_org_rule, rule, domain))

    return domain


def clear_asterisk(rule):
    if rule.find('*') < 0:
        return rule
    org_rule = rule
    rule = rule.strip('*')
    rule = rule.replace('/*.', '/')
    rule = re.sub(r'/([a-zA-Z0-9]+)\*\.', '/', rule)
    rule = re.sub(r'\*([a-zA-Z0-9_%]+)', '', rule)
    rule = re.sub(r'^([a-zA-Z0-9_%]+)\*', '', rule)
    # print('{:<50.50} => {:<30.30}'.format(org_rule, rule))
    return rule


def parse_rules(rules):
    global _org_rule
    ignore_lst = []
    direct_lst = []
    proxy_lst = []
    for line in rules:
        _org_rule = line
        if not line or line.startswith('!'):
            continue

        if line.find('.*') >= 0 or line.startswith('/'):
            ignore_lst.append(line)
            continue

        domain = ''
        if line.startswith('@@'):
            line = line.lstrip('@|.')
            domain = surmise_domain(line)
            direct_lst.append(domain) if domain else \
                ignore_lst.append(_org_rule)
            continue
        elif line.startswith('|'):
            line = line.lstrip('|')
        domain = surmise_domain(line)
        proxy_lst.append(domain) if domain else ignore_lst.append(_org_rule)

    proxy_lst = list(set(proxy_lst))
    direct_lst = list(set(direct_lst))

    direct_lst = [d for d in direct_lst if d not in proxy_lst]

    proxy_lst.sort()
    direct_lst.sort()

    # _write('gfw-direct.txt', direct_lst)
    # _write('gfw-proxy.txt', proxy_lst)
    # _write('gfw-ignore.txt', ignore_lst)
    return [direct_lst, proxy_lst]


def get_pac_tpl():
    pac_tpl = _pac_tpl_precise if _cfg.precise else _pac_tpl
    if _cfg.compress:
        pac_tpl = pac_tpl.split('.')
        pac_tpl.insert(-1, 'min')
        pac_tpl = '.'.join(pac_tpl)
    return resource_data(pac_tpl)


def generate():
    prepare()

    gfwlist_rules = fetch_gfwlist()
    user_rules = fetch_user_rules()

    func_parse = parse_rules_precise if _cfg.precise else parse_rules
    rules = [func_parse(user_rules), func_parse(gfwlist_rules)]

    rules = json.dumps(rules,
                       indent=None if _cfg.compress else 4,
                       separators=(',', ':') if _cfg.compress else None)
    generated = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    content = get_pac_tpl()
    content = replace(content, {'__VERSION__': __version__,
                                '__GENERATED__': generated,
                                '__MODIFIED__': _gfwlist_modified,
                                '__GFWLIST_FROM__': _gfwlist_from,
                                '__PROXY__': _cfg.proxy,
                                '__RULES__': rules})

    if not _cfg.output or _cfg.output == '-':
        return sys.stdout.write(content)
    with codecs.open(abspath(_cfg.output), 'w', 'utf-8') as fp:
        fp.write(content)


def main():
    generate()


if __name__ == '__main__':
    main()
