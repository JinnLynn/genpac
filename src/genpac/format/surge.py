from .base import formater, FmtBase, TPL_LEAD_COMMENT

_DEF_DIRECT = '''
# Local Area Network
DOMAIN-SUFFIX,local,DIRECT
IP-CIDR,192.168.0.0/16,DIRECT
IP-CIDR,10.0.0.0/8,DIRECT
IP-CIDR,172.16.0.0/12,DIRECT
IP-CIDR,127.0.0.0/8,DIRECT
IP-CIDR,100.64.0.0/10,DIRECT
'''

_DEF_POLICY = 'PROXY'


@formater('surge', desc='Surge代理规则', order=90)
class FmtSurge(FmtBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('policy', default=_DEF_POLICY,
                            metavar='POLICY', help=f'代理规则策略: 默认: {_DEF_POLICY}')
        cls.register_option('no-direct', default=False,
                            action='store_true', help='不包含直连规则')
        cls.register_option('no-final', default=False,
                            action='store_true', help='不包含FINAL规则')
        cls.register_option('set', default=False,
                            action='store_true', help='输出为规则集')

    def generate(self, replacements):
        rules = []

        if not self.options.no_direct:
            rules.append(_DEF_DIRECT.strip())
            for d in self.ignored_domains:
                rules.append(f'DOMAIN-SUFFIX,{d},DIRECT')

        for d in self.gfwed_domains:
            rules.append(f'DOMAIN-SUFFIX,{d},{self.options.policy}')

        if not self.options.no_final:
            rules.extend(['', 'FINAL,DIRECT'])

        replacements.update(__RULES__='\n'.join(rules))
        return super().generate(replacements)

    @property
    def tpl(self):
        tpl = [TPL_LEAD_COMMENT, '__RULES__']
        if not self.options.set:
            tpl.insert(1, '[Rule]')
        return '\n'.join(tpl) + '\n'
