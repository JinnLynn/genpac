# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import sys
import pytest
from contextlib import contextmanager

from genpac import GenPAC, formater, FmtBase
from tests.util import buildenv, join_etc
from tests.util import parametrize, skipif, xfail

@contextmanager
def add_formater():
    @formater('test')
    class FmtTest(FmtBase):
        def __init__(self, *args, **kwargs):
            super(FmtTest, self).__init__(*args, **kwargs)

        @classmethod
        def prepare(cls, parser):
            super().prepare(parser)
            cls.register_option('--test-a', default='va', metavar='ARGA')
            cls.register_option('--test-b', default='vb', metavar='ARGB')

    yield FmtTest

    if 'test' in GenPAC._formaters:
        del GenPAC._formaters['test']


# 测试添加格式化器
def test_add_formater():
    with add_formater() as fmt_cls:
        assert 'test' in GenPAC._formaters
        assert fmt_cls._name == 'test'
        assert GenPAC._formaters['test']['cls'] == fmt_cls
    assert 'test' not in GenPAC._formaters

# 参数配置解析
@parametrize('argv, expected_ret', [
    ('--format=test', ('va', 'vb')),
    ('--format=test --test-a=va2 --test-b=vb2', ('va2', 'vb2')),
    (['-c', join_etc('config-fmt-test.ini')], ('pa', 'pb')),
    (['-c', join_etc('config-fmt-test.ini'), '--test-a=va2', '--test-b=vb2'], ('va2', 'vb2')),
    ])
def test_formater_option(argv, expected_ret):
    with add_formater(), buildenv(argv=argv):
        gp = GenPAC()
        gp.parse_options()
        assert len(gp.jobs) == 1
        job = gp.jobs[0]
        ex_a, ex_b = expected_ret
        assert job.format == 'test'
        assert job.test_a == ex_a
        assert job.test_b == ex_b
