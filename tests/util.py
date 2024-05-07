import sys
import os
import pytest
from contextlib import contextmanager

import genpac

parametrize = pytest.mark.parametrize
skipif = pytest.mark.skipif
xfail = pytest.mark.xfail

_ETC_DIR = os.path.join(os.path.dirname(__file__), 'etc')
_TMP_DIR = os.path.join(os.path.dirname(__file__), 'tmp')

# 是否是自己的机子
is_own = sys.platform.startswith('darwin') and \
    ''.join(os.environ.values()).find('JinnLynn') >= 0
is_not_own = not is_own


def join_etc(*args):
    return os.path.join(_ETC_DIR, *args)


def join_tmp(*args):
    return os.path.join(_TMP_DIR, *args)


@contextmanager
def buildenv(envs=None, argv=None, **kwargs):
    envs = envs or {}
    argv = argv or []
    if isinstance(argv, str):
        argv = argv.split(' ')
    if not argv or argv[0] != 'genpac':
        argv.insert(0, 'genpac')

    envs.setdefault('GENPAC_TEST_TMP', _TMP_DIR)
    envs.setdefault('GENPAC_TEST_ETC', _ETC_DIR)
    for k, v in envs.items():
        os.environ[k] = v
    old_argv = sys.argv
    sys.argv = argv

    yield

    genpac.Generator._cache.clear()

    for k in envs.keys():
        if k in os.environ:
            del os.environ[k]
    sys.argv = old_argv
