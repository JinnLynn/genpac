import json

from ..template import TemplateFile
from ..util import conv_bool

from .base import formater, FmtBase

_TPL_PAC = TemplateFile('res/tpl-pac.js', True)
_TPL_PAC_MIN = TemplateFile('res/tpl-pac.min.js', True)
_TPL_PAC_PRECISE = TemplateFile('res/tpl-pac-precise.js', True)
_TPL_PAC_PRECISE_MIN = TemplateFile('res/tpl-pac-precise.min.js', True)


@formater('pac', desc='通过代理自动配置文件(PAC)系统或浏览器可自动选择合适的代理服务器.')
class FmtPAC(FmtBase):
    _default_tpl = _TPL_PAC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.options.pac_precise:
            self._default_tpl = _TPL_PAC_PRECISE
        if self.options.pac_compress:
            self._default_tpl = _TPL_PAC_MIN
            if self.options.pac_precise:
                self._default_tpl = _TPL_PAC_PRECISE_MIN

    @classmethod
    def arguments(cls, parser):
        group = super().arguments(parser)
        group.add_argument(
            '--pac-proxy', metavar='PROXY',
            help='代理地址, 如 SOCKS5 127.0.0.1:8080; SOCKS 127.0.0.1:8080')
        group.add_argument(
            '--pac-precise', action='store_true',
            help='精确匹配模式')
        group.add_argument(
            '--pac-compress', action='store_true',
            help='压缩输出')

        # 弃用的参数
        # group.add_argument(
        #     '-p', '--proxy', dest='pac_proxy', metavar='PROXY',
        #     help='已弃用参数, 等同于--pac-proxy, 后续版本将删除, 避免使用')
        # group.add_argument(
        #     '-P', '--precise', action='store_true',
        #     dest='pac_precise',
        #     help='已弃用参数, 等同于--pac-precise, 后续版本将删除, 避免使用')
        # group.add_argument(
        #     '-z', '--compress', action='store_true',
        #     dest='pac_compress',
        #     help='已弃用参数, 等同于--pac-compress, 后续版本将删除, 避免使用')
        return group

    @classmethod
    def config(cls, options):
        options['pac-proxy'] = {'replaced': 'proxy'}
        options['pac-compress'] = {'conv': conv_bool, 'replaced': 'compress'}
        options['pac-precise'] = {'conv': conv_bool, 'replaced': 'precise'}

    def pre_generate(self):
        if not self.options.pac_proxy:
            self.error('代理信息不存在，检查参数--pac-proxy或配置pac-proxy')
            return False
        return super().pre_generate()

    def generate(self, replacements):
        rules = json.dumps(
            self.precise_rules if self.options.pac_precise else self.rules,
            indent=None if self.options.pac_compress else 4,
            separators=(',', ':') if self.options.pac_compress else None)
        replacements.update({'__PROXY__': self.options.pac_proxy,
                             '__RULES__': rules})
        return self.replace(self.tpl, replacements)
