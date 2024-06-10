from ..util import conv_bool, b64encode
from .base import formater, FmtBase

_TPL = '''
[AutoProxy 0.2.9]
! __GENPAC__
! Generated: __GENERATED__
! GFWList Last-Modified: __MODIFIED__
! GFWList From: __GFWLIST_FROM__
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
        cls.register_option('list-raw', conv=conv_bool, default=False,
                            action='store_true', help='明文，不进行base64编码')

    def generate(self, replacements):
        gfwed = [f'||{s}' for s in self.gfwed_domains]
        replacements.update({'__GFWED_DOMAINS__': '\n'.join(gfwed).strip()})
        content = self.replace(self.tpl, replacements)
        return b64encode(content) if not self.options.list_raw else content
