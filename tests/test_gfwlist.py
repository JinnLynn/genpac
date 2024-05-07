import os
import pytest
from contextlib import contextmanager

from genpac import FmtBase
from genpac import Generator
from genpac.util import Namespace
from genpac.core import _GFWLIST_URL
from tests.util import is_not_own
from tests.util import parametrize, skipif

_LOCAL_PROXY = ['socks5://127.0.0.1:9527', 'http://127.0.0.1:9580']


# Generator使用类变量_cache缓存gfwlist内容
# 每次测试需手动清除
@contextmanager
def generator(option):
    Generator._cache.clear()
    gen = Generator(option, FmtBase)
    yield gen
    Generator._cache.clear()


@skipif(is_not_own, reason='proxy')
@parametrize('proxy', _LOCAL_PROXY)
def test_proxy(proxy):
    opt = Namespace(proxy=proxy)
    gen = Generator(opt, FmtBase)
    # opener = gen.init_opener()
    ret = gen.fetch_online('http://www.baidu.com')
    print(ret)
    assert ret is not None


def _opt_gl(**kwargs):
    kwargs.setdefault('gfwlist_url', _GFWLIST_URL)
    kwargs.setdefault('proxy', None)
    kwargs.setdefault('gfwlist_disabled', False)
    kwargs.setdefault('gfwlist_local', None)
    kwargs.setdefault('gfwlist_update_local', False)
    kwargs.setdefault('gfwlist_decoded_save', None)
    return Namespace(**kwargs)


def _fetch_gfwlist_online(opt):
    with generator(opt) as gen:
        assert Generator._cache == {}
        content, _, modified = gen.fetch_gfwlist()
        assert len(content) > 3000
        assert opt.gfwlist_url in Generator._cache


# 在线获取gfwlist
@parametrize('opt', [_opt_gl()])
def test_gfwlist_online(opt):
    with generator(opt) as gen:
        assert Generator._cache == {}
        content, _, modified = gen.fetch_gfwlist()
        assert len(content) > 3000
        assert opt.gfwlist_url in Generator._cache


@skipif(is_not_own, reason='proxy')
@parametrize('opt', [
    _opt_gl(proxy=_LOCAL_PROXY[0]),
    _opt_gl(proxy=_LOCAL_PROXY[1])])
def test_gfwlist_online_with_proxy(opt):
    test_gfwlist_online(opt)


def test_gfwlist_online_cache():
    opt = _opt_gl()
    with generator(opt) as gen:
        content = gen.fetch(opt.gfwlist_url)
        assert opt.gfwlist_url in Generator._cache
        assert Generator._cache[opt.gfwlist_url] == content
        # 修改缓存，第二次获取
        Generator._cache[opt.gfwlist_url] = 'test'
        gen2 = Generator(opt, FmtBase)
        content2 = gen2.fetch(opt.gfwlist_url)
        assert content != content2
        assert content2 == 'test'
    # 退出with被清除
    assert opt.gfwlist_url not in Generator._cache
