import os
import re

from netaddr import IPNetwork, IPRange, IPAddress

from ..util import FatalError
from ..util import conv_lower
from ..util import logger
from .base import formater, FmtBase

_CC_DEF = 'CN'
_IP_FAMILIES = ['4', '6', 'all']

# NOTE: 中国地区的数据来自IP_DATA_ASN 其它来自 IP_DATA_GEOLITE2
# REF: https://github.com/gaoyifan/china-operator-ip/
#      https://github.com/sapics/ip-location-db/tree/main/geolite2-country
_IP_DATA_ASN = {
    4: os.getenv('GP_RES_IP_ASN_4', 'https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt'),
    6: os.getenv('GP_RES_IP_ASN_6', 'https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt')
}
_IP_DATA_GEOLITE2 = {
    4: os.getenv('GP_RES_IP_GEOLITE2_4', 'https://raw.githubusercontent.com/sapics/ip-location-db/main/geolite2-country/geolite2-country-ipv4.csv'),
    6: os.getenv('GP_RES_IP_GEOLITE2_6', 'https://raw.githubusercontent.com/sapics/ip-location-db/main/geolite2-country/geolite2-country-ipv6.csv')
}


class IPInterface(FmtBase):
    def iter_ip_cidr(self, family, cc):
        family = str(family)
        if family not in ['4', '6', 'all']:
            raise ValueError('IP family MUST BE: 4, 6, all')
        if family in ['4', 'all']:
            yield from self._fetch_ip_data(4, cc)

        if family in ['6', 'all']:
            yield from self._fetch_ip_data(6, cc)

    def iter_ip_range(self, family, cc):
        for d in self.iter_ip_cidr(family, cc):
            yield IPAddress(d.first), IPAddress(d.last)

    def _fetch_ip_data(self, family, cc):
        if cc.lower() == 'cn':
            yield from self._fetch_ip_data_cn(family)
            return

        expr = re.compile(f'^[0-9a-f:,]+,{cc}' if family == 6 else f'^[0-9\\.,]+,{cc}',
                          flags=re.IGNORECASE)
        url = _IP_DATA_GEOLITE2[int(family)]
        content = self.fetch(url)
        if not content:
            raise FatalError('获取IP数据失败')
        count = 0
        size = 0
        for d in content.splitlines():
            d = d.strip()
            if not d or not expr.fullmatch(d):
                continue
            first, last, _ = d.split(',')
            d = IPRange(first, last)
            for n in d.cidrs():
                count = count + 1
                size = size + n.size
                yield n
        logger.debug(f'IPv{family}[{cc}]: {count} => {size:.2e}')

    def _fetch_ip_data_cn(self, family):
        url = _IP_DATA_ASN[int(family)]
        content = self.fetch(url)
        if not content:
            raise FatalError('获取IP数据失败')
        count = 0
        size = 0
        for ip in content.splitlines():
            ip = ip.strip()
            if not ip:
                continue
            net = IPNetwork(ip)
            count = count + 1
            size = size + net.size
            yield net
        logger.debug(f'IPv{family}[cn]: {count} => {size:.2e}')


@formater('ip', desc="国别IP地址列表")
class FmtIP(IPInterface):
    _FORCE_IGNORE_GFWLIST = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def prepare(cls, parser):
        super().prepare(parser)
        cls.register_option('cc', conv=conv_lower, default=_CC_DEF,
                            metavar='CC',
                            help=f'国家代码(ISO 3166-1) 默认: {_CC_DEF}')
        families = ', '.join(_IP_FAMILIES)
        cls.register_option('family', conv=conv_lower, default='4',
                            type=lambda s: s.lower(),
                            choices=_IP_FAMILIES,
                            help=f'IP类型 可选: {families} 默认: 4')

    def generate(self, replacements):
        return '\n'.join(str(i) for i in self.iter_ip_cidr(self.options.family, self.options.cc))
