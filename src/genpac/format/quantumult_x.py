from .base import formater, FmtBase

_TPL = '''
#! __GENPAC__
#! Generated: __GENERATED__
#! GFWList Last-Modified: __MODIFIED__
__GFWED_RULES__
final, direct
'''


@formater('qtx', desc='Quantumult X是iOS下一款功能强大的网络分析及代理工具.')
class FmtQuantumultX(FmtBase):
    _default_tpl = _TPL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self, replacements):
        def to_rule(r, a):
            return f'HOST-SUFFIX,{r},{a}'

        # direct_rules = [to_rule(r, 'direct') for r in self.ignored_domains]
        gfwed_rules = [to_rule(r, 'proxy') for r in self.gfwed_domains]
        # rules = gfwed_rules + direct_rules
        replacements.update({'__GFWED_RULES__': '\n'.join(gfwed_rules)})
        return self.replace(self.tpl, replacements)
