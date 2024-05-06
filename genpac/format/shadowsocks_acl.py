import re
import math
from IPy import IP, IPSet

from ..util import read_file, get_resource_path
from .base import formater, FmtBase

_TPL = '''
#! __GENPAC__
[bypass_all]

[proxy_list]
__GFWED_RULES__
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''


@formater('ssacl', desc='Shadowsocks访问控制列表.')
class FmtSSACL(FmtBase):
    _default_tpl = _TPL

    def __init__(self, *args, **kwargs):
        super(FmtSSACL, self).__init__(*args, **kwargs)

        if self.options.ssacl_geocn:
            self.options.gfwlist_disabled = True

    @classmethod
    def arguments(cls, parser):
        group = super(FmtSSACL, cls).arguments(parser)
        group.add_argument(
            '--ssacl-geocn', action='store_true',
            help='国内IP不走代理，所有国外IP走代理')
        return group

    @classmethod
    def config(cls, options):
        options['ssacl-geocn'] = {'default': False}

    @property
    def tpl(self):
        if self.options.ssacl_geocn:
            return ('#! __GENPAC__\n'
                    '#! Generated: __GENERATED__\n'
                    '[proxy_all]\n\n'
                    '[bypass_list]\n'
                    '__CNIPS__\n')
        else:
            return ('#! __GENPAC__\n'
                    '#! Generated: __GENERATED__\n'
                    '#! GFWList: __GFWLIST_DETAIL__\n'
                    '[bypass_all]\n\n'
                    '[proxy_list]\n'
                    '__GFWED_RULES__\n')

    def generate(self, replacements):
        return self.gen_by_geoip(replacements) if self.options.ssacl_geocn else \
            self.gen_by_gfwlist(replacements)

    def gen_by_gfwlist(self, replacements):
        def parse_rules(rules):
            rules = [r.replace('.', '\\.') for r in rules]
            rules = ['(^|\\.){}$'.format(r) for r in rules]
            return rules

        gfwed_rules = parse_rules(self.gfwed_domains)

        replacements.update({
            '__GFWED_RULES__': '\n'.join(gfwed_rules)})

        return self.replace(self.tpl, replacements)

    def gen_by_geoip(self, replacements):
        ips = self.fetch_cnips()
        ip_data = []
        for ip in ips:
            ip_data.append({
                'ip': ip.strNormal(wantprefixlen=0),
                'prefixlen': ip.prefixlen(),
                'netmask': ip.netmask(),
                'broadcast': ip.broadcast(),
                'net': ip.net(),
                'int': ip.int(),
                'hex': ip.strHex(wantprefixlen=0),
                'bin': ip.strBin(wantprefixlen=0)
            })
        # fmt = '{ip} {prefixlen} {netmask} {broadcast} {net} {int} {hex} {bin}'
        fmt = '{ip}/{prefixlen}'
        ip_data = [fmt.format(**d) for d in ip_data]
        print(len(ip_data))
        replacements.update({
            '__CNIPS__': '\n'.join(ip_data)})
        return self.replace(self.tpl, replacements)

    def fetch_cnips(self):
        data = read_file(get_resource_path('res/ipdata.txt'))

        cnregex = re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*',
                             re.IGNORECASE)

        results = []
        for item in cnregex.findall(data):
            units = item.split('|')
            start_ip = units[3]
            ip_count = int(units[4])
            prefixlen = 32 - int(math.log(ip_count, 2))
            results.append(IP('{}/{}'.format(start_ip, prefixlen)))

        return IPSet(results)
