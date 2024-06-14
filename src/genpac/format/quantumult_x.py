from .base import formater, FmtBase, TPL_LEAD_COMMENT


@formater('qtx', desc='Quantumult X 的分流规则')
class FmtQuantumultX(FmtBase):
    _default_tpl = f'{TPL_LEAD_COMMENT}\n__RULES__\n'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('no-direct', default=False,
                            action='store_true', help='不包含直连规则')
        cls.register_option('no-final', default=False,
                            action='store_true', help='不包含FINAL规则')

    def generate(self, replacements):
        rules = []
        if not self.options.no_direct:
            rules.extend([f'HOST-SUFFIX,{r},DIRECT' for r in self.ignored_domains])

        rules.extend([f'HOST-SUFFIX,{r},PROXY' for r in self.gfwed_domains])

        if not self.options.no_final:
            rules.append('\nFINAL,DIRECT')

        replacements.update(__RULES__='\n'.join(rules))
        return super().generate(replacements)
