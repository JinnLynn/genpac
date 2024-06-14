import json
import yaml

from ..util import conv_lower
from .base import formater, FmtBase, TPL_LEAD_COMMENT


# 更合乎习惯的list缩进
# REF: https://stackoverflow.com/a/39681672/1952172
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


V2RAY_DUMPER = {'json': lambda d: json.dumps(d, indent=4),
                'yaml': lambda d: f'{TPL_LEAD_COMMENT}\n' + yaml.dump(d, Dumper=Dumper, indent=2, sort_keys=False)}

_DEF_PROXY_TAG = 'proxy'
_DEF_FORMAT = list(V2RAY_DUMPER.keys())[0]


@formater('v2ray', desc='V2Ray的路由规则', order=-80)
class FmtV2Ray(FmtBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('proxy', default=_DEF_PROXY_TAG,
                            metavar='TAG',
                            help=f'代理标签，默认: {_DEF_PROXY_TAG}')
        cls.register_option('direct', default=None,
                            metavar='TAG',
                            help='直连标签，未指定则不输出直连规则')
        cls.register_option('default', default=None,
                            metavar='TAG',
                            help='默认标签，未指定则不输出默认规则')
        cls.register_option('format', conv=conv_lower, default=_DEF_FORMAT,
                            choices=V2RAY_DUMPER.keys(),
                            help=f'输出格式，默认: {_DEF_FORMAT}')

    def pre_generate(self):
        if self.options.format not in V2RAY_DUMPER.keys():
            self.error(f'输出的格式错误，只能是: {list(V2RAY_DUMPER.keys())}')
            return False
        return super().pre_generate()

    @property
    def tpl(self):
        rules = []
        if self.options.direct:
            rules.append(dict(outboundTag=self.options.direct,
                              type='field',
                              domains=[f'domain:{d}' for d in self.ignored_domains if d]))
        if self.options.proxy:
            rules.append(dict(outboundTag=self.options.proxy,
                              type='field',
                              domains=[f'domain:{d}' for d in self.gfwed_domains if d]))
        if self.options.default:
            rules.append(dict(outboundTag=self.options.default,
                              type='field',
                              port='0-65535'))
        data = {
            'routing': {
                'domainStrategy': 'AsIs',
                'rules': rules
            }
        }
        return V2RAY_DUMPER[self.options.format](data)
