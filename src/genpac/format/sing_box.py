from ..util import conv_lower, Namespace, dump_json
from .base import formater
from .ip import IPInterface, _IP_FAMILIES, _CC_DEF


@formater('sing', desc='Sing-Box路由规则集(Rule-Set)')
class FmtSingBox(IPInterface):
    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('ip', default=False,
                            action='store_true', help='默认输出规则基于域名，当指定该选项时输出基于IP的规则')
        cls.register_option('ip-cc', conv=conv_lower, default=_CC_DEF,
                            metavar='CC',
                            help=f'当输出基于IP规则时的国家代码(ISO 3166-1) 默认: {_CC_DEF}')
        cls.register_option('ip-family', conv=conv_lower, default='4',
                            type=lambda s: s.lower(),
                            choices=_IP_FAMILIES,
                            help=f'当输出基于IP规则时的类型 可选: {', '.join(_IP_FAMILIES)} 默认: 4')

    def generate(self, replacements):
        data = Namespace(version=1, rules=[])
        if not self.options.ip:
            data.rules.append({
                'domain_suffix': self.gfwed_domains
            })
        else:
            data.rules.append({
                'ip_cidr': [str(d) for d in self.iter_ip_cidr(self.options.ip_family, self.options.ip_cc)]
            })
        return dump_json(data)
