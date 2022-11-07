import json

from .base import formater, FmtBase

@formater('v2ray', desc='V2Ray')
class FmtV2Ray(FmtBase):
    _DEF_PROXY_TAG = 'proxy'
    _DEF_DIRECT_TAG = 'direct'

    def __init__(self, *args, **kwargs):
        super(FmtV2Ray, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtV2Ray, cls).arguments(parser)
        group.add_argument(
            '--v2ray-proxy-tag', metavar='TAG',
            help='走代理流量标签，默认: {}'.format(cls._DEF_PROXY_TAG))
        group.add_argument(
            '--v2ray-direct-tag', metavar='TAG',
            help='直连流量标签，默认: {}'.format(cls._DEF_DIRECT_TAG))
        group.add_argument(
            '--v2ray-protocol', metavar='PROTOCOL[,PROTOCOL]',
            help='protocol')
        group.add_argument(
            '--v2ray-pretty',
        )
        return group

    @classmethod
    def config(cls, options):
        options['v2ray-proxy-tag'] = {'default': cls._DEF_PROXY_TAG}
        options['v2ray-direct-tag'] = {'default': cls._DEF_DIRECT_TAG}

    def generate(self, replacements):
        gfwed_rules = {
            'outboundTag': self.options.v2ray_proxy_tag,
            'type': 'field',
            'domains': ['domain:{}'.format(d) for d in self.gfwed_domains]
        }
        direct_rules = {
            'outboundTag': self.options.v2ray_direct_tag,
            'type': 'field',
            'port': '0-65535'
        }
        return json.dumps({
            'routing': {
                'domainStrategy': 'AsIs',
                'rules': [gfwed_rules, direct_rules]
            }
        }, indent=4)

    def generate_v5(self, replacements):
        gfwed_rules = {
            'tag': self.options.v2ray_proxy_tag,
            'domains': [{'type': 'RootDomain', 'value': d} for d in self.gfwed_domains]
        }
        return json.dumps({
            'routing': {
                'domainStrategy': 'AsIs',
                'rule': [gfwed_rules, {'tag': self.options.v2ray_direct_tag}]
            }
        }, indent=2)
