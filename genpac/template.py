# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from ._compat import string_types
from .util import get_resource_path, read_file


class TemplateFile:
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
#! genpac __VERSION__ https://github.com/JinnLynn/genpac
__DNSMASQ__
#! Generated: __GENERATED__
#! GFWList: __MODIFIED__ From __GFWLIST_FROM__
'''
SS_ACL = '''
# Shadowsocks Access Control List
# genpac __VERSION__ https://github.com/JinnLynn/genpac
[bypass_all]

[proxy_list]
__GFWED_RULES__
# Generated: __GENERATED__
# GFWList: __MODIFIED__ From __GFWLIST_FROM__
'''
POTATSO = '''
#! genpac __VERSION__ https://github.com/JinnLynn/genpac
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
#! GFWList: __MODIFIED__ From __GFWLIST_FROM__
'''

# 去除模板的前后换行符
for name in dir():
    if name.isupper() and isinstance(vars()[name], string_types):
        vars()[name] = vars()[name].strip('\n')
