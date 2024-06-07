
from base64 import b64decode
from collections import OrderedDict

from .base import formater, FmtBase

# == Wingy ==
_TPL_WINGY = '''
#! __GENPAC__
version: 2
adapter:
__ADAPTER__
rule:
    - type: iplist
      adapter: direct
      criteria:
        - 127.0.0.0/8
        - 192.168.0.0/16
        - 10.0.0.0/8
        - 224.0.0.0/8
        - 169.254.0.0/16
    - type: dnsfail
      adapter: __RULE_ADAPTER_ID__
    - type: domainlist
      adapter: __RULE_ADAPTER_ID__
      criteria:
__CRITERIA__
#! Generated: __GENERATED__
#! GFWList: __MODIFIED__ From __GFWLIST_FROM__
'''


@formater('wingy', desc='Wingy是iOS下基于NEKit的代理App. \n* 注意: 即将废弃 *')
class FmtWingy(FmtBase):
    _default_tpl = _TPL_WINGY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super().arguments(parser)
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
        domains = [f'{fmt}- s,{s}' for s in self.gfwed_domains]

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
            for k, v in opts.items():
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


# == Potatso ==
_TPL_POTATSO = '''
#! __GENPAC__
[RULESET.gfwed]
name = "GFWed rules"
rules = [
__GFWED_RULES__
]

[RULESET.direct]
name = "Direct rules"
rules = [
__DIRECT_RULES__
]
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''


@formater('potatso', desc='Potatso2是iOS下基于NEKit的代理App, 无可选参数. \n* 注意: 即将废弃 *')
class FmtPotatso(FmtBase):
    _default_tpl = _TPL_POTATSO

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self, replacements):
        def to_rule(r, a):
            return '{:>4}"DOMAIN-SUFFIX, {}, {}"'.format('', r, a)

        direct_rules = [to_rule(r, 'DIRECT') for r in self.ignored_domains]
        gfwed_rules = [to_rule(r, 'PROXY') for r in self.gfwed_domains]
        replacements.update({
            '__DIRECT_RULES__': ',\n'.join(direct_rules),
            '__GFWED_RULES__': ',\n'.join(gfwed_rules)})
        return self.replace(self.tpl, replacements)
