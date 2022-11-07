import itertools

from .. import template as tpl
from .base import FmtBase, formater

_TPL = '''
#! __GENPAC__
__DNSMASQ__
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''

@formater('dnsmasq', desc='Dnsmasq配合iptables ipset可实现基于域名的自动直连或代理.')
class FmtDnsmasq(FmtBase):
    _default_tpl = _TPL
    _default_dns = '127.0.0.1#53'
    _default_ipset = 'GFWLIST'

    def __init__(self, *args, **kwargs):
        super(FmtDnsmasq, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtDnsmasq, cls).arguments(parser)
        group.add_argument(
            '--dnsmasq-dns', metavar='DNS',
            help='生成规则域名查询使用的DNS服务器，格式: HOST#PORT\n'
                 '默认: {}'.format(cls._default_dns))
        group.add_argument(
            '--dnsmasq-ipset', metavar='IPSET',
            help='转发使用的ipset名称, 默认: {}'.format(cls._default_ipset))
        return group

    @classmethod
    def config(cls, options):
        options['dnsmasq-dns'] = {'default': cls._default_dns}
        options['dnsmasq-ipset'] = {'default': cls._default_ipset}

    def generate(self, replacements):
        dns = self.options.dnsmasq_dns
        ipset = self.options.dnsmasq_ipset

        servers = ['server=/{}/{}'.format(s, dns) for s in self.gfwed_domains]
        ipsets = ['ipset=/{}/{}'.format(s, ipset) for s in self.gfwed_domains]
        merged_lst = list(itertools.chain.from_iterable(zip(servers, ipsets)))

        replacements.update({'__DNSMASQ__': '\n'.join(merged_lst).strip()})
        return self.replace(self.tpl, replacements)
