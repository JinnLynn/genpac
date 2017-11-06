# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os

from genpac import Config, GenPAC
from tests.util import buildenv, _TMP_DIR, join_tmp
from tests.util import parametrize, skipif, xfail

# 测试配置文件
# =====

def test_config(config_file):
    parser = Config()
    parser.read(config_file)
    assert isinstance(parser.section('config'), dict)
    assert isinstance(parser.section('job'), dict)
    assert isinstance(parser.sections('job'), list)
    assert len(parser.sections('job')) > 1


# 替换环境变量
def test_config_env(config_file):
    def get_test_env():
        parser = Config()
        parser.read(config_file)
        return parser.section('config')['test-env']

    # 存在环境变量，将替换
    with buildenv():
        assert get_test_env() == _TMP_DIR

    # 不存在环境变量
    assert get_test_env() == '${GENPAC_TEST_TMP}'


@parametrize('argv, expected_rule, expected_rule_from',[
    ('', [], []),
    ('--user-rule=,,, --user-rule-from=,,,', [], []),
    ('--user-rule=a,b,c --user-rule-from=~/a.txt,b.txt,/c.txt',
     ['a', 'b', 'c'],
     [os.path.expanduser('~/a.txt'), os.path.abspath('b.txt'), os.path.abspath('/c.txt')]),
    ('--user-rule=a --user-rule=b,c --user-rule-from=/a, --user-rule-from=/b,/c',
     ['a', 'b', 'c'],
     ['/a', '/b', '/c'])
    ])
def test_argv_list(argv, expected_rule, expected_rule_from):
    with buildenv(argv=argv):
        gp = GenPAC()
        gp.parse_options()
        assert len(gp.jobs) == 1
        job = gp.jobs[0]
        assert job.user_rule == expected_rule
        assert job.user_rule_from == expected_rule_from
