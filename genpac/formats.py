# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import re
import json
import itertools
from collections import OrderedDict
from base64 import b64decode
from pprint import pprint  # noqa: F401

from ._compat import iteritems, text_type
from . import Namespace, TemplateFile, formater, parse_rules
from .util import error, conv_bool
from .util import read_file, get_resource_path, replace_all
from . import template as tpl


class FmtBase(object):
    _name = ''
    _desc = None
    _default_tpl = None

    def __init__(self, *args, **kwargs):
        super(FmtBase, self).__init__()
        self.options = kwargs.get('options') or Namespace()

        self._update_orginal_rules(
            kwargs.get('user_rules') or [],
            kwargs.get('gfwlist_rules') or [])

    @classmethod
    def arguments(cls, parser):
        return parser.add_argument_group(title=cls._name.upper(),
                                         description=cls._desc or '')

    @classmethod
    def config(cls, options):
        pass

    def pre_generate(self):
        return True

    def generate(self, replacements):
        return self.replace(self.tpl, replacements)

    def post_generate(self):
        pass

    @property
    def tpl(self):
        if self.options.template:
            return text_type(TemplateFile(self.options.template))
        return text_type(self._default_tpl)

    def error(self, msg):
        error('{}格式生成错误: {}'.format(self._name.upper(), msg))

    def replace(self, text, replacements):
        return replace_all(text, replacements)

    @property
    def rules(self):
        if self._rules is None:
            self._rules = [parse_rules(self._orginal_user_rules),
                           parse_rules(self._orginal_gfwlist_rules)]
        return self._rules

    @property
    def precise_rules(self):
        if self._precise_rules is None:
            self._precise_rules = [
                parse_rules(self._orginal_user_rules, True),
                parse_rules(self._orginal_gfwlist_rules, True)]
        return self._precise_rules

    @property
    def gfwed_domains(self):
        if self._gfwed_domains is None:
            self._gfwed_domains = list(
                set(self.rules[0][1] + self.rules[1][1]))
            self._gfwed_domains.sort()
        return self._gfwed_domains

    @property
    def ignored_domains(self):
        if self._ignored_domains is None:
            self._ignored_domains = list(
                set(self.rules[0][0] + self.rules[1][0]))
            self._ignored_domains.sort()
        return self._ignored_domains

    def _update_orginal_rules(self, user_rules, gfwlist_rules):
        self._orginal_user_rules = user_rules
        self._orginal_gfwlist_rules = gfwlist_rules
        self._rules = None
        self._precise_rules = None
        self._gfwed_domains = None
        self._ignored_domains = None


@formater('pac', desc='通过代理自动配置文件(PAC)系统或浏览器可自动选择合适的代理服务器.')
class FmtPAC(FmtBase):
    _default_tpl = tpl.PAC

    def __init__(self, *args, **kwargs):
        super(FmtPAC, self).__init__(*args, **kwargs)

        if self.options.pac_precise:
            self._default_tpl = tpl.PAC_PRECISE
        if self.options.pac_compress:
            self._default_tpl = tpl.PAC_MIN
            if self.options.pac_precise:
                self._default_tpl = tpl.PAC_PRECISE_MIN

    @classmethod
    def arguments(cls, parser):
        group = super(FmtPAC, cls).arguments(parser)
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
        return group

    @classmethod
    def config(cls, options):
        options['pac-proxy'] = {'replaced': 'proxy'}
        options['pac-compress'] = {'conv': conv_bool, 'replaced': 'compress'}
        options['pac-precise'] = {'conv': conv_bool, 'replaced': 'precise'}

    def pre_generate(self):
        if not self.options.pac_proxy:
            self.error('代理信息不存在，检查参数--pac-proxy或配置pac-proxy')
            return False
        return super(FmtPAC, self).pre_generate()

    def generate(self, replacements):
        rules = json.dumps(
            self.precise_rules if self.options.pac_precise else self.rules,
            indent=None if self.options.pac_compress else 4,
            separators=(',', ':') if self.options.pac_compress else None)
        replacements.update({'__PROXY__': self.options.pac_proxy,
                             '__RULES__': rules})
        return self.replace(self.tpl, replacements)


@formater('dnsmasq', desc='Dnsmasq配合iptables ipset可实现基于域名的自动直连或代理.')
class FmtDnsmasq(FmtBase):
    _default_tpl = tpl.DNSMASQ
    _default_dns = '127.0.0.1#53'
    _default_ipset = 'GFWLIST'

    def __init__(self, *args, **kwargs):
        super(FmtDnsmasq, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtDnsmasq, cls).arguments(parser)
        group.add_argument(
            '--dnsmasq-dns', metavar='DNS',
            help='生成规则域名查询使用的DNS服务器，格式: HOST#PORT\n'
                 '默认: {}'.format(cls._default_dns))
        group.add_argument(
            '--dnsmasq-ipset', metavar='IPSET',
            help='转发使用的ipset名称, 默认: {}'.format(cls._default_ipset))
        return group

    @classmethod
    def config(cls, options):
        options['dnsmasq-dns'] = {'default': cls._default_dns}
        options['dnsmasq-ipset'] = {'default': cls._default_ipset}

    def generate(self, replacements):
        dns = self.options.dnsmasq_dns
        ipset = self.options.dnsmasq_ipset

        servers = ['server=/{}/{}'.format(s, dns) for s in self.gfwed_domains]
        ipsets = ['ipset=/{}/{}'.format(s, ipset) for s in self.gfwed_domains]
        merged_lst = list(itertools.chain.from_iterable(zip(servers, ipsets)))

        replacements.update({'__DNSMASQ__': '\n'.join(merged_lst).strip()})
        return self.replace(self.tpl, replacements)


@formater('ss-acl', desc='Shadowsocks访问控制列表, 本格式没有可选参数.')
class FmtSSACL(FmtBase):
    _default_tpl = tpl.SS_ACL

    def __init__(self, *args, **kwargs):
        super(FmtSSACL, self).__init__(*args, **kwargs)

    def generate(self, replacements):
        def parse_rules(rules):
            rules = [l.replace('.', '\\.') for l in rules]
            rules = ['(^|\\.){}$'.format(l) for l in rules]
            return rules

        gfwed_rules = parse_rules(self.gfwed_domains)

        replacements.update({
            '__GFWED_RULES__': '\n'.join(gfwed_rules)})

        return self.replace(self.tpl, replacements)


@formater('wingy', desc='Wingy是iOS下基于NEKit的代理App.')
class FmtWingy(FmtBase):
    _default_tpl = tpl.WINGY

    def __init__(self, *args, **kwargs):
        super(FmtWingy, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtWingy, cls).arguments(parser)
        group.add_argument(
            '--wingy-adapter-opts', metavar='OPTS',
            help='adapter选项, 选项间使用`,`分割, 多个adapter使用`;`分割, 如:\n'
                 '  id:ap1,type:http,host:127.0.0.1,port:8080;'
                 'id:ap2,type:socks5,host:127.0.0.1,port:3128')
        group.add_argument(
            '--wingy-rule-adapter-id', metavar='ID',
            help='生成规则使用的adapter ID')
        return group

    @classmethod
    def config(cls, options):
        options['wingy-adapter-opts'] = {}
        options['wingy-rule-adapter-id'] = {}

    def generate(self, replacements):
        fmt = '{:>8}'.format(' ')
        domains = ['{}- s,{}'.format(fmt, s) for s in self.gfwed_domains]

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


@formater('potatso', desc='Potatso2是iOS下基于NEKit的代理App, 本格式没有可选参数.')
class FmtPotatso(FmtBase):
    _default_tpl = tpl.POTATSO

    def __init__(self, *args, **kwargs):
        super(FmtPotatso, self).__init__(*args, **kwargs)

    def generate(self, replacements):
        def to_rule(r, a):
            return '{:>4}"DOMAIN-SUFFIX, {}, {}"'.format('', r, a)

        direct_rules = [to_rule(r, 'DIRECT') for r in self.ignored_domains]
        gfwed_rules = [to_rule(r, 'PROXY') for r in self.gfwed_domains]
        replacements.update({
            '__DIRECT_RULES__': ',\n'.join(direct_rules),
            '__GFWED_RULES__': ',\n'.join(gfwed_rules)})
        return self.replace(self.tpl, replacements)


@formater('surge', desc='Surge是基于(Network Extension)API开发的一款网络调试工具, '
                        '亦可用于翻墙, 本格式没有可选参数.')
class FmtSurge(FmtBase):
    _default_tpl = tpl.SURGE

    def __init__(self, *args, **kwargs):
        super(FmtSurge, self).__init__(*args, **kwargs)

    def generate(self, replacements):
        def to_rule(r, a):
            return 'DOMAIN-SUFFIX,{},{}'.format(r, a)

        direct_rules = [to_rule(r, 'DIRECT') for r in self.ignored_domains]
        gfwed_rules = [to_rule(r, 'PROXY') for r in self.gfwed_domains]
        rules = gfwed_rules + direct_rules
        replacements.update({
            '__RULES__': '\n'.join(rules)})
        return self.replace(self.tpl, replacements)


@formater('quantumult', desc='Quantumult是iOS下支持多种协议的的代理App, '
                             '兼容Surge规则, 本格式没有可选参数.')
class FmtQuantumult(FmtSurge):
    pass


@formater('shadowrocket', desc='Shadowrocket是iOS下支持多种协议的的代理App, '
                               '兼容Surge规则, 本格式没有可选参数.')
class FmtShadowrocket(FmtSurge):
    pass
