import json

from ..template import TemplateFile
from ..util import conv_bool
from .base import formater, FmtBase

_TPL_PAC = TemplateFile('res/tpl-pac.js', True)
_TPL_PAC_MIN = TemplateFile('res/tpl-pac.min.js', True)
_TPL_PAC_PRECISE = TemplateFile('res/tpl-pac-precise.js', True)
_TPL_PAC_PRECISE_MIN = TemplateFile('res/tpl-pac-precise.min.js', True)


@formater('pac', desc='通过代理自动配置文件(PAC)系统或浏览器可自动选择合适的代理服务器', order=-100)
class FmtPAC(FmtBase):
    _default_tpl = _TPL_PAC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.options.precise:
            self._default_tpl = _TPL_PAC_PRECISE
        if self.options.compress:
            self._default_tpl = _TPL_PAC_MIN
            if self.options.precise:
                self._default_tpl = _TPL_PAC_PRECISE_MIN

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('proxy',
                            metavar='PROXY',
                            help='代理地址, 如 SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080')
        cls.register_option('precise', conv=conv_bool,
                            action='store_true', help='精确匹配模式')
        cls.register_option('compress', conv=conv_bool,
                            action='store_true', help='压缩输出')

    def pre_generate(self):
        if not self.options.proxy:
            self.error('代理信息不存在，检查参数--pac-proxy或配置pac-proxy')
            return False
        return super().pre_generate()

    def generate(self, replacements):
        rules = json.dumps(
            self.precise_rules if self.options.precise else self.rules,
            indent=None if self.options.compress else 4,
            separators=(',', ':') if self.options.compress else None)
        replacements.update({'__PROXY__': self.options.proxy,
                             '__RULES__': rules})
        return self.replace(self.tpl, replacements)
