
from .base import formater, FmtBase

_TPL = '''
#! __GENPAC__
[Rule]
__RULES__

# Local Area Network
DOMAIN-SUFFIX,local,DIRECT
IP-CIDR,192.168.0.0/16,DIRECT
IP-CIDR,10.0.0.0/8,DIRECT
IP-CIDR,172.16.0.0/12,DIRECT
IP-CIDR,127.0.0.0/8,DIRECT
IP-CIDR,100.64.0.0/10,DIRECT

FINAL,DIRECT

#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''

_DESC = '''Surge是基于(Network Extension)API开发的一款网络调试工具, 亦可做为代理使用。
以下APP也可使用该格式规则:
    * QuantumultX
    * Shadowrocket
本格式没有可选参数
'''


@formater('surge', desc=_DESC)
class FmtSurge(FmtBase):
    _default_tpl = _TPL

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
