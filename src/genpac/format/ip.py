import re

from netaddr import IPNetwork, IPRange

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
    4: 'https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt',
    6: 'https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt'
}
_IP_DATA_GEOLITE2 = {
    4: 'https://raw.githubusercontent.com/sapics/ip-location-db/main/geolite2-country/geolite2-country-ipv4.csv',
    6: 'https://raw.githubusercontent.com/sapics/ip-location-db/main/geolite2-country/geolite2-country-ipv6.csv'
}


class IPList(list):
    def add(self, item):
        if isinstance(item, IPNetwork):
            self.append(item)
        elif isinstance(item, IPRange):
            self.extend(item.cidrs())
        else:
            raise ValueError('ONLY IPNetwork or IPRange')

    @property
    def size(self):
        return sum(item.size for item in self)

    def iter_cidrs(self):
        return self


@formater('ip', desc="国别IP地址列表")
class FmtIP(FmtBase):
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
        ip4s, ip6s = self._generate_by_cc(self.options.cc)
        output = ip4s + ip6s
        return '\n'.join([str(i) for i in output])

    @property
    def _ipv4(self):
        return self.options.family in [4, '4', 'all']

    @property
    def _ipv6(self):
        return self.options.family in [6, '6', 'all']

    def _ip_network(self, data):
        try:
            if isinstance(data, str):
                return IPNetwork(data)
            elif isinstance(data, tuple):
                first, last = data
                return IPRange(first, last)
            raise ValueError('IP数据类型错误')
        except Exception as e:
            logger.warning(f'解析IP地址错误: {data} {e} {type(e)}')
            return None

    def _generate_by_cc(self, cc):
        ip4s = IPList()
        ip6s = IPList()

        record = 0

        if self._ipv4:
            for d in self._fetch_data(4, cc):
                ip_net = self._ip_network(d)
                if ip_net:
                    ip4s.add(ip_net)
                record = record + 1
            logger.debug(f'IPv4[{cc}]: Nums: {ip4s.size:.2e} '
                         f'Record: {record} => {len(ip4s.iter_cidrs())}')

        record = 0
        if self._ipv6:
            record = 0
            for d in self._fetch_data(6, cc):
                ip_net = self._ip_network(d)
                if ip_net:
                    ip6s.add(ip_net)
                record = record + 1

            logger.debug(f'IPv6[{cc}]: Nums: {ip6s.size:.2e} '
                         f'Record: {record} => {len(ip6s.iter_cidrs())}')

        return ip4s, ip6s

    def _fetch_data_cn(self, family):
        url = _IP_DATA_ASN[int(family)]
        content = self.fetch(url)
        if not content:
            raise FatalError('获取IP数据失败')
        for ip in content.splitlines():
            ip = ip.strip()
            if not ip:
                continue
            yield ip

    def _fetch_data(self, family, cc):
        if cc.lower() == 'cn':
            yield from self._fetch_data_cn(family)
            return

        expr = re.compile(f'^[0-9a-f:,]+,{cc}' if family == 6 else f'^[0-9\\.,]+,{cc}',
                          flags=re.IGNORECASE)
        url = _IP_DATA_GEOLITE2[int(family)]
        content = self.fetch(url)
        if not content:
            raise FatalError('获取IP数据失败')
        for d in content.splitlines():
            d = d.strip()
            if not d or not expr.fullmatch(d):
                continue
            first, last, _ = d.split(',')
            yield (first, last)
