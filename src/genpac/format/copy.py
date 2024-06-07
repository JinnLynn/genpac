from os import path

from .base import formater, FmtBase
from ..util import open_file, FatalError


@formater('copy', desc="IP地址列表")
class FMTCopy(FmtBase):
    _FORCE_IGNORE_GFWLIST = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super().arguments(parser)
        group.add_argument('--copy-from', metavar='SRC',
                           help='来源, 网址或文件路径')
        return group

    @classmethod
    def config(cls, options):
        options['copy-from'] = {}

    def generate(self, replacements):
        content = ''
        try:
            if path.isfile(self.options.copy_from):
                with open_file(self.options.copy_from) as fp:
                    content = fp.read()
            else:
                content = self.generator.fetch(self.options.copy_from)
                if content is None:
                    raise Exception
        except Exception:
            raise FatalError(f'copy: 无法读取或下载文件 {self.options.copy_from}')
        return content
