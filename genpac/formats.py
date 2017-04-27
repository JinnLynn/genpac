# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import re
import json
import itertools
from collections import OrderedDict
from base64 import b64decode

from ._compat import unquote, urlparse
from ._compat import iteritems
from . import formater, Namespace
from .publicsuffix import get_public_suffix
from .util import error, conv_bool
from .util import read_file, get_resource_path, get_resource_data


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

    def replace(self, text, adict):
        def one_xlat(match):
            return adict[match.group(0)]
        rx = re.compile('|'.join(map(re.escape, adict)))
        return rx.sub(one_xlat, text)

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
            elif line.startswith('|') or line.endswith('|'):
                line = line.strip('|')
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
        dat_path = get_resource_path('res/public_suffix_list.dat')
        domain = get_public_suffix(host, dat_path)
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


@formater('pac')
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
            '-p', '--proxy', dest='pac_proxy', metavar='PROXY',
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
        return self.replace(self.tpl, replacements)


@formater('dnsmasq')
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
        return self.replace(self.tpl, replacements)


@formater('wingy')
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
        content, _ = read_file(self.options.wingy_template,
                               fail_msg='读取wingy模板文件{path}失败')
        return content

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
            '__CRITERIA__': '\n'.join(domains)})
        return self.replace(self.tpl, replacements)

    def _parse_adapter(self):
        def split(txt, sep):
            return [s.strip() for s in txt.split(sep) if s.strip()]

        def to_yaml(opts):
            tmp = []
            for k, v in iteritems(opts):
                tmp.append('{:>6}{}: {}'.format('', k, v))
            tmp[0] = '{:>4}- {}'.format('', tmp[0].strip())
            return '\n'.join(tmp)

        def ss_uri(aid, uri):
            encoded = uri.lstrip('ss://').lstrip('//').rstrip('=') + '=='
            decoded = b64decode(encoded).decode('utf-8')
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
            for v in k_v:
                od.setdefault(v.split(':')[0].strip(),
                              v.split(':')[1].strip())
            if 'ss' in od:
                od = ss_uri(od['id'], od['ss'])
            opts.append(to_yaml(od))
        return '\n'.join(opts)
