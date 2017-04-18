# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import sys
import warnings

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
        message.encode('utf-8'), GenPACDeprecationWarning, stacklevel=4)


def check_deprecated_args():
    for k, v in _deprecated_args.iteritems():
        if k not in sys.argv:
            continue
        new, ver = v
        deprecation(
            '在{}中参数{}已被弃用, 即将移除, 可使用: {}'.format(ver, k, new))


def check_deprecated_config(keys):
    for k in keys:
        if k not in _deprecated_config:
            continue
        new, ver = _deprecated_config[k]
        deprecation(
            '在{}中配置选项{}已被弃用, 即将移除, 可使用: {}'.format(ver, k, new))
