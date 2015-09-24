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

from .pysocks.socks import PROXY_TYPES as _proxy_types
from .pysocks.sockshandler import SocksiPyHandler

__version__ = '1.3.0'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2015 JinnLynn'

__all__ = ['main']

_default_url = 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'
_proxy_types['SOCKS'] = _proxy_types['SOCKS4']
_proxy_types['PROXY'] = _proxy_types['HTTP']

_help_tpl = 'res/help.txt'
_pac_tpl = 'res/pac-tpl.js'
_pac_tpl_min = 'res/pac-tpl.min.js'
_pac_tpl_base64 = 'res/pac-tpl.base64.js'
_config_sample = 'res/config-sample.ini'
_user_rule_sample = 'res/user-rules-sample.txt'

_ret = argparse.Namespace()
_cfg = None


class HelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super(HelpAction, self).__init__(option_strings, dest, nargs=0,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        with codecs.open(pkgdata(_help_tpl), 'r', 'utf-8') as fp:
            print(fp.read())
        parser.exit()


def abspath(path):
    if not path:
        return path
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


def pkgdata(path):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    return os.path.join(dir_path, path)


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    if kwargs.get('exit', False):
        sys.exit(1)


def replace(content, replaces):
    for k, v in replaces.items():
        content = content.replace(k, v)
    return content


def parse_args():
    parser = argparse.ArgumentParser(
        prog='genpac',
        add_help=False
    )
    parser.add_argument('-p', '--proxy')
    parser.add_argument('--gfwlist-url', default=None)
    parser.add_argument('--gfwlist-proxy')
    parser.add_argument('--gfwlist-local')
    parser.add_argument('--update-gfwlist-local', action='store_true',
                        default=None)
    parser.add_argument('--user-rule', action='append')
    parser.add_argument('--user-rule-from', action='append')
    parser.add_argument('-o', '--output')
    parser.add_argument('-c', '--config-from')
    parser.add_argument('-z', '--compress', action='store_true', default=None)
    parser.add_argument('--base64', action='store_true', default=None)
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
            args.update_gfwlist_local = conv_bool(
                update('update_gfwlist_local', 'update-gfwlist-local', False))
            args.proxy = update('proxy', 'proxy')
            args.user_rule_from = update('user_rule_from', 'user-rule-from')
            args.output = update('output', 'output')
            args.compress = conv_bool(update('compress', 'compress', False))
            args.base64 = conv_bool(update('base64', 'base64', False))
            if not args.gfwlist_url:
                args.gfwlist_url = _default_url
            if args.base64:
                args.compress = True
        except:
            error('read config file fail.', exit=True)
    args.user_rule = list_v(args.user_rule)
    args.user_rule_from = list_v(args.user_rule_from)
    return args


def prepare():
    global _cfg, _ret
    _cfg = parse_config()
    _cfg.output = _cfg.output
    _cfg.gfwlist_local = _cfg.gfwlist_local

    init_sample()

    if _cfg.base64:
        error('WARNING: some brower DO NOT support pac file '
              'which was encoded by base64.')

    _ret.version = __version__
    _ret.generated = ''
    _ret.modified = ''
    _ret.gfwlist_from = ''
    _ret.proxy = _cfg.proxy if _cfg.proxy else 'DIRECT'
    _ret.rules = ''


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
        shutil.copyfile(pkgdata(_config_sample), config_dst)
        shutil.copyfile(pkgdata(_user_rule_sample), user_rule_dst)
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
        error('gfwlist proxy error.', exit=True)


def fetch_gfwlist():
    global _ret
    content = ''
    try:
        opener = build_opener()
        res = opener.open(_cfg.gfwlist_url)
        content = res.read()
    except:
        try:
            with codecs.open(abspath(_cfg.gfwlist_local), 'r', 'utf-8') as fp:
                content = fp.read()
            _ret.gfwlist_from = 'local[{}]'.format(_cfg.gfwlist_local)
        except:
            pass
    else:
        _ret.gfwlist_from = 'online[{}]'.format(_cfg.gfwlist_url)
        if _cfg.gfwlist_local and _cfg.update_gfwlist_local:
            with codecs.open(abspath(_cfg.gfwlist_local), 'w', 'utf-8') as fp:
                fp.write(content)

    if not content:
        if _cfg.gfwlist_url != '-' or _cfg.gfwlist_local:
            error('fetch gfwlist fail.', exit=True)
        else:
            _ret.gfwlist_from = 'unused'

    try:
        content = '! {}'.format(base64.decodestring(content))
        content = content.splitlines()
        for line in content:
            if line.startswith('!') and 'Last Modified' in line:
                _ret.modified = line.split(':', 1)[1].strip()
                break
    except:
        pass
    if not _ret.modified:
        _ret.modified = '-'

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


def parse_rules(rules):
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


def generate(gfwlist_rules, user_rules):
    global _ret
    rules = [parse_rules(user_rules), parse_rules(gfwlist_rules)]
    _ret.rules = json.dumps(rules,
                            indent=None if _cfg.compress else 4,
                            separators=(',', ':') if _cfg.compress else None)
    _ret.generated = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())


def output():
    pac_tpl = pkgdata(_pac_tpl_min if _cfg.compress else _pac_tpl)
    with codecs.open(pac_tpl, 'r', 'utf-8') as fp:
        content = fp.read()

    content = replace(content, {'__VERSION__': _ret.version,
                                '__GENERATED__': _ret.generated,
                                '__MODIFIED__': _ret.modified,
                                '__GFWLIST_FROM__': _ret.gfwlist_from,
                                '__PROXY__': _ret.proxy,
                                '__RULES__': _ret.rules})

    if _cfg.base64:
        with codecs.open(pkgdata(_pac_tpl_base64), 'r', 'utf-8') as fp:
            b64_content = fp.read()
            content = replace(b64_content,
                              {'__BASE64__': base64.b64encode(content),
                               '__VERSION__': _ret.version})

    file_ = sys.stdout
    if _cfg.output and _cfg.output != '-':
        file_ = codecs.open(abspath(_cfg.output), 'w', 'utf-8')
    file_.write(content)


def main():
    prepare()

    gfwlist = fetch_gfwlist()
    user_rules = fetch_user_rules()

    generate(gfwlist, user_rules)

    output()

if __name__ == '__main__':
    main()
