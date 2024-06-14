from ..util import conv_bool, b64encode
from .base import formater, FmtBase, _lead_comment_tpl

_TPL = f'''
[AutoProxy 0.2.9]
{_lead_comment_tpl(prefix='')}
__GFWED_DOMAINS__
'''


@formater('list', desc="与GFWList格式相同的地址列表")
class FmtList(FmtBase):
    _default_tpl = _TPL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('raw', conv=conv_bool, default=False,
                            action='store_true', help='明文，不进行base64编码')

    def generate(self, replacements):
        ignored = [f'@@||{s}' for s in self.ignored_domains]
        gfwed = [f'||{s}' for s in self.gfwed_domains]
        replacements.update({'__GFWED_DOMAINS__': '\n'.join(ignored + gfwed).strip()})
        content = self.replace(self.tpl, replacements)
        return b64encode(content) if not self.options.raw else content
