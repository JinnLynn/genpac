import itertools

from ..util import conv_list
from .base import FmtBase, formater, TPL_LEAD_COMMENT

_DEF_DNS = '127.0.0.1#53'


@formater('dnsmasq', desc='Dnsmasq配合iptables/ipset、nftables/nftset可实现基于域名的透明代理', order=-90)
class FmtDnsmasq(FmtBase):
    _default_tpl = f'{TPL_LEAD_COMMENT}\n__DNSMASQ__\n'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('dns', default=_DEF_DNS,
                            metavar='DNS',
                            help='生成规则域名查询使用的DNS服务器，格式: HOST#PORT\n'
                                 f'默认: {_DEF_DNS}')
        cls.register_option('ipset', conv=conv_list,
                            action='append', metavar='IPSET',
                            help='使用ipset, 允许重复或使用`,`分割多个, \n'
                                 '如: GFWLIST,GFWLIST6')
        cls.register_option('nftset', conv=conv_list,
                            action="append", metavar='NFTSET',
                            help='使用ntfset, 允许重复或使用`,`分割多个, \n'
                                 '如: 4#GFWLIST,6#GFWLIST6')

    def generate(self, replacements):
        dns = self.options.dns
        ipset = ','.join(self.options.ipset)
        nftset = ','.join(self.options.nftset)

        result = [
            [f'server=/{s}/{dns}' for s in self.gfwed_domains]
        ]
        if ipset:
            result.append([f'ipset=/{s}/{ipset}' for s in self.gfwed_domains])
        if nftset:
            result.append([f'nftset=/{s}/{nftset}' for s in self.gfwed_domains])
        result = list(itertools.chain.from_iterable(zip(*result)))

        replacements.update(__DNSMASQ__='\n'.join(result))
        return super().generate(replacements)
