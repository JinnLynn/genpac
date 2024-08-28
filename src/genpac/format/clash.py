from ..util import dump_yaml
from .base import formater, FmtBase, TPL_LEAD_COMMENT


_DEF_DIRECT = [
    'DOMAIN-SUFFIX,local,DIRECT',
    'IP-CIDR,192.168.0.0/16,DIRECT',
    'IP-CIDR,10.0.0.0/8,DIRECT',
    'IP-CIDR,172.16.0.0/12,DIRECT',
    'IP-CIDR,127.0.0.0/8,DIRECT',
    'IP-CIDR,100.64.0.0/10,DIRECT'
]
_DEF_POLICY = 'PROXY'


@formater('clash', desc='Clash的代理规则', order=89)
class FmtClash(FmtBase):
    _default_tpl = f'{TPL_LEAD_COMMENT}\n__RULES__\n'

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
                            action='store_true', help='输出Rule-Set')
        cls.register_option('set-direct', default=False,
                            action='store_true', help='输出Rule-Set时默认输出代理规则，使用该选项则输出直连规则')

    def generate(self, replacements):
        data = self.generate_rule_set() if self.options.set else self.generate_rule()
        replacements.update(__RULES__=dump_yaml(data))
        return super().generate(replacements)

    def generate_rule(self):
        rules = []
        if not self.options.no_direct:
            rules.extend(_DEF_DIRECT)
            for d in self.ignored_domains:
                rules.append(f'DOMAIN-SUFFIX,{d},DIRECT')

        for d in self.gfwed_domains:
            rules.append(f'DOMAIN-SUFFIX,{d},{self.options.policy}')

        if not self.options.no_final:
            rules.append('MATCH,DIRECT')

        return {'rules': rules}

    def generate_rule_set(self):
        rules = [f'DOMAIN-SUFFIX,{d}' for d in (self.gfwed_domains if not self.options.set_direct else self.ignored_domains)]
        return {'payload': rules}
