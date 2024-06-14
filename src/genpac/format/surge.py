from .base import formater, FmtBase, TPL_LEAD_COMMENT

_TPL = f'''
{TPL_LEAD_COMMENT}
[Rule]
__RULES__

FINAL,DIRECT
'''

_TPL_SET = f'''
{TPL_LEAD_COMMENT}
__RULES__
'''

_DEF_DIRECT = '''
# Local Area Network
DOMAIN-SUFFIX,local,DIRECT
IP-CIDR,192.168.0.0/16,DIRECT
IP-CIDR,10.0.0.0/8,DIRECT
IP-CIDR,172.16.0.0/12,DIRECT
IP-CIDR,127.0.0.0/8,DIRECT
IP-CIDR,100.64.0.0/10,DIRECT
'''

_DESC = '''Surge是基于(Network Extension)API开发的一款网络调试工具, 亦可做为代理使用
以下APP也可使用该格式规则:
    * Shadowrocket
'''
_PROXY_POLICY = 'PROXY'


@formater('surge', desc=_DESC, order=90)
class FmtSurge(FmtBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._default_tpl = _TPL_SET if self.options.set else _TPL

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('policy', default=_PROXY_POLICY,
                            metavar='POLICY', help=f'代理规则策略: 默认: {_PROXY_POLICY}')
        cls.register_option('direct', default=False,
                            action='store_true', help='输出直连规则，默认仅输出代理规则')
        cls.register_option('set', default=False,
                            action='store_true', help='输出为规则集')

    def generate(self, replacements):
        rules = []

        if self.options.direct:
            rules.append(_DEF_DIRECT.strip())
            for d in self.ignored_domains:
                rules.append(f'DOMAIN-SUFFIX,{d},DIRECT')

        for d in self.gfwed_domains:
            rules.append(f'DOMAIN-SUFFIX,{d},{self.options.policy}')

        replacements.update(__RULES__='\n'.join(rules))
        return super().generate(replacements)
