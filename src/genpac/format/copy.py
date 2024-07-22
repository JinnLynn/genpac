from os import path

from .base import formater, FmtBase
from ..util import FatalError


@formater('copy', desc="IP地址列表")
class FmtCopy(FmtBase):
    _FORCE_IGNORE_GFWLIST = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('source', metavar='SRC', help='来源, 网址或文件路径')

    def generate(self, replacements):
        content = None
        try:
            if path.isfile(self.options.source):
                with open(self.options.source, 'rb') as fp:
                    content = fp.read()
            else:
                content = self.fetch(self.options.source, decode=False)
                if content is None:
                    raise Exception
        except Exception:
            raise FatalError(f'copy: 无法读取或下载文件 {self.options.source}')
        return content
