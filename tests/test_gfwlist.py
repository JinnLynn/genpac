# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import pytest
from contextlib import contextmanager

from genpac import GenPAC, Generator, Namespace, FmtBase
from genpac.core import _GFWLIST_URL
from tests.util import is_not_own
from tests.util import parametrize, skipif, xfail

_LOCAL_PROXY = ['SOCKS5 127.0.0.1:9527', 'PROXY 127.0.0.1:9580']


# Generator使用类变量_gfwlists缓存gfwlist内容
# 每次测试需手动清除
@contextmanager
def generator(option):
    Generator._gfwlists.clear()
    gen = Generator(option, FmtBase)
    yield gen
    Generator._gfwlists.clear()


@skipif(is_not_own, reason='proxy')
@parametrize('proxy', _LOCAL_PROXY)
def test_proxy(proxy):
    opt = Namespace(gfwlist_proxy=proxy)
    gen = Generator(opt, FmtBase)
    opener = gen.init_opener()
    res = opener.open('http://www.baidu.com')
    assert res.getcode() == 200


def _opt_gl(**kwargs):
    kwargs.setdefault('gfwlist_url', _GFWLIST_URL)
    kwargs.setdefault('gfwlist_proxy', None)
    kwargs.setdefault('gfwlist_disabled', False)
    kwargs.setdefault('gfwlist_local', None)
    kwargs.setdefault('gfwlist_update_local', False)
    kwargs.setdefault('gfwlist_decoded_save', None)
    return Namespace(**kwargs)


def _fetch_gfwlist_online(opt):
    with generator(opt) as gen:
        assert Generator._gfwlists == {}
        content, _, modified = gen.fetch_gfwlist()
        assert len(content) > 3000
        assert opt.gfwlist_url in Generator._gfwlists


# 在线获取gfwlist
@parametrize('opt', [_opt_gl()])
def test_gfwlist_online(opt):
    with generator(opt) as gen:
        assert Generator._gfwlists == {}
        content, _, modified = gen.fetch_gfwlist()
        assert len(content) > 3000
        assert opt.gfwlist_url in Generator._gfwlists


@skipif(is_not_own, reason='proxy')
@parametrize('opt', [
    _opt_gl(gfwlist_proxy=_LOCAL_PROXY[0]),
    _opt_gl(gfwlist_proxy=_LOCAL_PROXY[1])])
def test_gfwlist_online_with_proxy(opt):
    test_gfwlist_online(opt)


def test_gfwlist_online_cache():
    opt = _opt_gl()
    with generator(opt) as gen:
        content = gen.fetch_gfwlist_online()
        assert opt.gfwlist_url in Generator._gfwlists
        assert Generator._gfwlists[opt.gfwlist_url] == content
        # 修改缓存，第二次获取
        Generator._gfwlists[opt.gfwlist_url] = 'test'
        gen2 = Generator(opt, FmtBase)
        content2 = gen2.fetch_gfwlist_online()
        assert content != content2
        assert content2 == 'test'
    # 退出with被清除
    assert opt.gfwlist_url not in Generator._gfwlists
