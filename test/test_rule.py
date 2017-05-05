# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import pytest
from genpac import parse_rules

from test.util import parametrize, skipif, xfail

# 规则解析测试
# =====

def _rs(r):
    if r is None:
        return []
    return r if isinstance(r, list) else [r]

def _r(rule, d=None, p=None, dw=None, dr=None, pw=None, pr=None):
    def is_w2r(r):
        if r is None or r.startswith('^') or r.endswith('$'):
            return False
        return True
    _re_pre = '^[\\w\\-]+:\\/+(?!\\/)(?:[^\\/]+\\.)?'
    if is_w2r(dr):
        dr = _re_pre + dr
    if is_w2r(pr):
        pr = _re_pre + pr
    return (rule,
            [_rs(d), _rs(p)],
            [_rs(dr), _rs(dw), _rs(pr), _rs(pw)])

_pars = [
    _r(''),
    _r('!google.com'),
    _r('@@sina.com', d='sina.com', dw='*sina.com*'),
    _r('@@||163.com', d='163.com', dr='163\\.com'),
    _r('@@abc', dw='*abc*'),
    _r('twitter.com', p='twitter.com', pw='*twitter.com*'),
    _r('||youtube.com', p='youtube.com', pr='youtube\\.com'),
    _r('.google.com', p='google.com', pw='*.google.com*'),
    _r('/^https?:\/\/[^\/]+blogspot\.(.*)/', pr='^https?:\/\/[^\/]+blogspot\.(.*)'),
    _r('/^https?:\/\/([^\/]+\.)*google\.(ac|ad)\/.*/',
       p=['google.ac', 'google.ad'],
       pr='^https?:\/\/([^\/]+\.)*google\.(ac|ad)\/.*'),
    _r('|http://85st.com', p='85st.com', pr='^http://85st\.com'),
    _r('http://85st.com|', p='85st.com', pr='http://85st\.com$'),
    _r('|http://85st.com|', p='85st.com', pr='^http://85st\.com$'),
    _r('test.ae.org', p='test.ae.org', pw='*test.ae.org*'),
    _r('test.ad.org', p='ad.org', pw='*test.ad.org*'),
    _r('google', pw='*google*'),
    # s3.amazonaws.com在public_suffix_list中存在,所以被认为是顶级域名
    _r('test.s3.amazonaws.com', p='test.s3.amazonaws.com', pw='*test.s3.amazonaws.com*'),
    # amazonaws.com在public_suffix_list中存在
    _r('test.s4.amazonaws.com', p='s4.amazonaws.com', pw='*test.s4.amazonaws.com*'),
    _r('测试.公司.hk', p='测试.公司.hk', pw='*测试.公司.hk*')
]

def merge():
    mr = []
    mer = [[], []]
    mepr = [[], [], [], []]
    for r, er, epr in _pars:
        mr.append(r)
        mer[0].extend(er[0])
        mer[1].extend(er[1])
        mepr[0].extend(epr[0])
        mepr[1].extend(epr[1])
        mepr[2].extend(epr[2])
        mepr[3].extend(epr[3])
    mer[0] = list(set(mer[0]))
    mer[1] = list(set(mer[1]))
    mer[0] = [d for d in mer[0] if d not in mer[1]]
    mer[0].sort()
    mer[1].sort()
    return (mr, mer, mepr)

_pars.append(merge())


@parametrize('rule, expected_ret, expected_precise_ret', _pars)
def test_rule_parse(rule, expected_ret, expected_precise_ret):
    rules = rule if isinstance(rule, list) else [rule]
    ret = parse_rules(rules)
    assert ret == expected_ret
    ret = parse_rules(rules, True)
    assert ret == expected_precise_ret
