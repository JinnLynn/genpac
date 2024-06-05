import json
import yaml

from .base import formater, FmtBase


# 更合乎习惯的list缩进
# REF: https://stackoverflow.com/a/39681672/1952172
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(Dumper, self).increase_indent(flow, False)


V2RAY_DUMPER = {'json': lambda d: json.dumps(d, indent=4),
                'yaml': lambda d: yaml.dump(d, Dumper=Dumper, indent=2, sort_keys=False)}


@formater('v2ray', desc='V2Ray')
class FmtV2Ray(FmtBase):
    _DEF_PROXY_TAG = 'proxy'
    _DEF_FORMAT = list(V2RAY_DUMPER.keys())[0]

    def __init__(self, *args, **kwargs):
        super(FmtV2Ray, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtV2Ray, cls).arguments(parser)
        group.add_argument(
            '--v2ray-proxy-tag', metavar='TAG',
            help=f'走代理流量标签，默认: {cls._DEF_PROXY_TAG}')
        group.add_argument(
            '--v2ray-direct-tag', metavar='TAG',
            help='直连流量标签，未指定则不输出直连规则')
        group.add_argument(
            '--v2ray-format', choices=V2RAY_DUMPER.keys(),
            help=f'输出格式，默认: {cls._DEF_FORMAT}'
        )
        return group

    @classmethod
    def config(cls, options):
        options['v2ray-proxy-tag'] = {'default': cls._DEF_PROXY_TAG}
        options['v2ray-direct-tag'] = {'default': None}
        options['v2ray-format'] = {'default': cls._DEF_FORMAT}

    def generate(self, replacements):
        rules = []
        if self.options.v2ray_proxy_tag:
            rules.append(dict(outboundTag=self.options.v2ray_proxy_tag,
                              type='field',
                              domains=[f'domain:{d}' for d in self.gfwed_domains if d]))
        if self.options.v2ray_direct_tag:
            rules.append(dict(outboundTag=self.options.v2ray_direct_tag,
                              type='field',
                              port='0-65535'))
        data = {
            'routing': {
                'domainStrategy': 'AsIs',
                'rules': rules
            }
        }
        return V2RAY_DUMPER[self.options.v2ray_format](data)
