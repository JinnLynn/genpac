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
        cls.register_option('ipset-direct', conv=conv_list, default='_GP_DIRECT',
                            action='append', metavar='IPSET',
                            help='直连的ipset, 防止某些情况下直连IP被误添加到需代理的列表, 置空则不输出\n'
                                 '一般不需要设置，默认: _GP_DIRECT')
        cls.register_option('nftset', conv=conv_list,
                            action="append", metavar='NFTSET',
                            help='使用ntfset, 需2.87+, 允许重复或使用`,`分割多个, \n'
                                 '如: 4#inet#TABLE_NAME#SET_NAME_4,6#inet#TABLE_NAME#SET_NAME_6')
        cls.register_option('nftset-direct', conv=conv_list, default='4#inet#_GP_DIRECT#_GP_DIRECT',
                            action='append', metavar='NFTSET',
                            help='直连的ipset, 防止某些情况下直连IP被误添加到需代理的列表, 置空则不输出\n'
                                 '一般不需要设置，默认: 4#inet#_GP_DIRECT#_GP_DIRECT')
        cls.register_option('no-direct', default=False,
                            action='store_true', help='不包含直连规则')

    def generate(self, replacements):
        dns = self.options.dns
        ipset = ','.join(self.options.ipset)
        nftset = ','.join(self.options.nftset)
        ipset_direct = ','.join(self.options.ipset_direct)
        nftset_direct = ','.join(self.options.nftset_direct)

        ignored = []
        gfwed = []

        if self.options.dns:
            gfwed.append([f'server=/{s}/{dns}' for s in self.gfwed_domains])

        if ipset:
            gfwed.append([f'ipset=/{s}/{ipset}' for s in self.gfwed_domains])

        if nftset:
            gfwed.append([f'nftset=/{s}/{nftset}' for s in self.gfwed_domains])

        if not self.options.no_direct:
            ignored.append([f'server=/{s}/#' for s in self.ignored_domains])
            if ipset and ipset_direct:
                ignored.append([f'ipset=/{s}/{ipset_direct}' for s in self.ignored_domains])
            if nftset and nftset_direct:
                ignored.append([f'nftset=/{s}/{nftset_direct}' for s in self.ignored_domains])

        ignored = list(itertools.chain.from_iterable(zip(*ignored)))
        gfwed = list(itertools.chain.from_iterable(zip(*gfwed)))

        replacements.update(__DNSMASQ__='\n'.join(ignored + gfwed))
        return super().generate(replacements)
