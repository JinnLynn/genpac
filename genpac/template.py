# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from ._compat import string_types
from .util import get_resource_path, read_file


# 模板文件
# is_buildin == True时为内建模板文件，在脚本源码目录下寻找
class TemplateFile(object):
    def __init__(self, path, is_buildin=False):
        self.tpl_file = get_resource_path(path) if is_buildin else path

    def __str__(self):
        return read_file(self.tpl_file, fail_msg='读取自定义模板文件{path}失败')


PAC = TemplateFile('res/tpl-pac.js', True)
PAC_MIN = TemplateFile('res/tpl-pac.min.js', True)
PAC_PRECISE = TemplateFile('res/tpl-pac-precise.js', True)
PAC_PRECISE_MIN = TemplateFile('res/tpl-pac-precise.min.js', True)
WINGY = TemplateFile('res/tpl-wingy.yaml', True)
DNSMASQ = '''
#! __GENPAC__
__DNSMASQ__
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''
SS_ACL = '''
#! __GENPAC__
[bypass_all]

[proxy_list]
__GFWED_RULES__
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''
POTATSO = '''
#! __GENPAC__
[RULESET.gfwed]
name = "GFWed rules"
rules = [
__GFWED_RULES__
]

[RULESET.direct]
name = "Direct rules"
rules = [
__DIRECT_RULES__
]
#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''
SURGE = '''
#! __GENPAC__
[Rule]
__RULES__

# Local Area Network
DOMAIN-SUFFIX,local,DIRECT
IP-CIDR,192.168.0.0/16,DIRECT
IP-CIDR,10.0.0.0/8,DIRECT
IP-CIDR,172.16.0.0/12,DIRECT
IP-CIDR,127.0.0.0/8,DIRECT
IP-CIDR,100.64.0.0/10,DIRECT

FINAL,DIRECT

#! Generated: __GENERATED__
#! GFWList: __GFWLIST_DETAIL__
'''

# 去除文本模板的前后换行符
for name in dir():
    if name.isupper() and isinstance(vars()[name], string_types):
        vars()[name] = vars()[name].strip('\n')
