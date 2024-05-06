import itertools

from .base import FmtBase, formater
from ..util import conv_list

_TPL = '''
#! __GENPAC__
__DNSMASQ__
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''


@formater('dnsmasq', desc='Dnsmasq配合iptables/ipset、nftables/nftset可实现基于域名的透明代理.')
class FmtDnsmasq(FmtBase):
    _default_tpl = _TPL
    _default_dns = '127.0.0.1#53'

    def __init__(self, *args, **kwargs):
        super(FmtDnsmasq, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtDnsmasq, cls).arguments(parser)
        group.add_argument(
            '--dnsmasq-dns', metavar='DNS',
            help='生成规则域名查询使用的DNS服务器，格式: HOST#PORT\n'
                 f'默认: {cls._default_dns}')
        group.add_argument(
            '--dnsmasq-ipset', action='append', metavar='IPSET',
            help='使用ipset, 允许重复或使用`,`分割多个, \n'
                 '如: GFWLIST,GFWLIST6')
        group.add_argument(
            '--dnsmasq-nftset', action="append", metavar='NFTSET',
            help='使用ntfset, 允许重复或使用`,`分割多个, \n'
                 '如: 4#GFWLIST,6#GFWLIST6')
        return group

    @classmethod
    def config(cls, options):
        options['dnsmasq-dns'] = {'default': cls._default_dns}
        options['dnsmasq-ipset'] = {'conv': conv_list}
        options['dnsmasq-nftset'] = {'conv': conv_list}

    def generate(self, replacements):
        dns = self.options.dnsmasq_dns
        ipset = ','.join(self.options.dnsmasq_ipset)
        nftset = ','.join(self.options.dnsmasq_nftset)

        result = [
            [f'server=/{s}/{dns}' for s in self.gfwed_domains]
        ]
        if ipset:
            result.append([f'ipset=/{s}/{ipset}' for s in self.gfwed_domains])
        if nftset:
            result.append([f'nftset=/{s}/{nftset}' for s in self.gfwed_domains])
        result = list(itertools.chain.from_iterable(zip(*result)))

        replacements.update({'__DNSMASQ__': '\n'.join(result).strip()})
        return self.replace(self.tpl, replacements)
