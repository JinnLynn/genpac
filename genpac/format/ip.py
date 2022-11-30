import re
import math

from IPy import IP, IPSet

from .base import formater, FmtBase
from ..util import conv_lower, conv_path
from ..util import logger, write_file, read_file

IP_CC_DEF = 'CN'
IP_DATA_DEF = 'https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'

@formater('ip', desc="IP地址列表")
class FmtIP(FmtBase):
    # _default_tpl = _TPL

    def __init__(self, *args, **kwargs):
        super(FmtIP, self).__init__(*args, **kwargs)

    @classmethod
    def arguments(cls, parser):
        group = super(FmtIP, cls).arguments(parser)
        group.add_argument('--ip-cc', metavar='CC',
                           help='国家代码(ISO 3166-2) 默认: {}'.format(IP_CC_DEF))
        group.add_argument('--ip-data-url', metavar='URL',
                           help='IP数据地址 \n默认: {}'.format(IP_DATA_DEF))
        group.add_argument('--ip-data-local', metavar='FILE',
                           help='IP数据本地, 当在线地址获取失败时使用')
        group.add_argument('--ip-data-update-local', action='store_true',
                           help='当在线IP数据成功获取且--ip-data-local参数存在时, '
                                '更新IP数据本地文件内容')
        return group

    @classmethod
    def config(cls, options):
        options['ip-cc'] = {'conv': conv_lower, 'default': IP_CC_DEF}
        options['ip-data-url'] = {'default': IP_DATA_DEF}
        options['ip-data-local'] = {'conv': conv_path}
        options['ip-data-update-local'] = {'default': False}

    def generate(self, replacements):
        content = self._fetch_data()

        cc = self.options.ip_cc or r'[a-z]{2}'
        regex = re.compile(r'apnic\|' + cc + r'\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*',
                           re.IGNORECASE)
        ret = []
        for item in regex.findall(content):
            parts = item.split('|')
            ret.append(IP('{}/{:d}'.format(parts[3],
                                        int(32 - math.log(float(parts[4]), 2)))))
        org_len = len(ret)
        ret = IPSet(ret)
        logger.debug('IP[%s] parsed: %d => %d', self.options.ip_cc, org_len, len(ret.prefixes))
        return '\n'.join([str(i) for i in ret])

    def _fetch_data(self):
        try:
            content = self.generator.fetch(self.options.ip_data_url)
            if not content:
                raise ValueError()
            if self.options.ip_data_local \
                    and self.options.ip_data_update_local:
                write_file(self.options.ip_data_local, content,
                           fail_msg='更新本地IPData文件{path}失败')
        except Exception:
            if self.options.ip_data_local:
                content = read_file(self.options.ip_data_local,
                                    fail_msg='读取本地IPData文件{path}失败')
        return content
