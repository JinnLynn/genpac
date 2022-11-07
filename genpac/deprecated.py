# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import sys
import warnings

from .util import error

_warnings_showwarning = None

_deprecated_args = {
    '-p': ('--pac-proxy', '2.0'),
    '--proxy': ('--pac-proxy', '2.0'),
    '-z': ('--pac-compress', '2.0'),
    '--compress': ('--pac-compress', '2.0'),
    '-P': ('--pac-precise', '2.0'),
    '--precise': ('--pac-precise', '2.0')
}

_deprecated_config = {
    'proxy': ('pac-proxy', '2.0'),
    'compress': ('pac-compress', '2.0'),
    'precise': ('pac-precise', '2.0')
}


class GenPACDeprecationWarning(DeprecationWarning):
    pass


warnings.simplefilter('always', GenPACDeprecationWarning)


def deprecation(message):
    warnings.warn(
        message, GenPACDeprecationWarning, stacklevel=4)


def check_deprecated_args():
    for k, v in _deprecated_args.items():
        if k not in sys.argv:
            continue
        new, ver = v
        deprecation(
            '在{}中参数{}已被{}取代, 后续版本将删除, 避免使用.'.format(ver, k, new))


def check_deprecated_config(keys):
    for k in keys:
        if k not in _deprecated_config:
            continue
        new, ver = _deprecated_config[k]
        deprecation(
            '在{}中配置选项{}已被{}取代, 后续版本将删除, 避免使用.'.format(ver, k, new))


def _showwarning(message, category, filename, lineno, file=None, line=None):
    if not issubclass(category, GenPACDeprecationWarning):
        if _warnings_showwarning is not None:
            _warnings_showwarning(
                message, category, filename, lineno, file, line,
            )
    else:
        error('{}: {}'.format(category.__name__, message))


def install_showwarning():
    global _warnings_showwarning

    if _warnings_showwarning is None:
        _warnings_showwarning = warnings.showwarning
        warnings.showwarning = _showwarning
