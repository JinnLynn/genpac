# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
from genpac import Config, GenPAC

from test.util import buildenv, _TMP_DIR, join_tmp
from test.util import parametrize, skipif, xfail

# 测试配置文件
# =====

def test_config(config_file):
    parser = Config()
    parser.parse(config_file)
    assert isinstance(parser.options('default'), dict)
    assert isinstance(parser.options('config'), dict)
    assert isinstance(parser.options('config', True), list)
    assert len(parser.options('config', True)) > 1


# 替换环境变量
def test_config_env(config_file):
    def get_test_env():
        parser = Config()
        parser.parse(config_file)
        return parser.options('default')['test-env']

    # 存在环境变量，将替换
    with buildenv():
        assert get_test_env() == _TMP_DIR

    # 不存在环境变量
    assert get_test_env() == '${GENPAC_TEST_TMP}'


@parametrize('argv, expected_ret',[
    ('--format=dnsmasq', []),
    ('--format=dnsmasq --user-rule-from=,,,', []),
    ('--format=dnsmasq --user-rule-from=~/a.txt,b.txt,/c.txt',
     [os.path.expanduser('~/a.txt'), os.path.abspath('b.txt'), os.path.abspath('/c.txt')])
    ])
def test_rule_from(argv, expected_ret):
    gfwlist_local = ''
    with buildenv(argv=argv):
        gp = GenPAC()
        gp.parse_options()
        assert len(gp.jobs) == 1
        job = gp.jobs[0]
        assert job.user_rule_from == expected_ret
