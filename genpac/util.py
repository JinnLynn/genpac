# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import sys
import codecs


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    if kwargs.get('exit', False):
        sys.exit(kwargs.get('exit_code', None) or 1)


def exit_error(*args, **kwargs):
    error(*args, exit=True, exit_code=kwargs.get('code') or 1)


def exit_success(*args):
    print(*args)
    sys.exit()


def abspath(path):
    if not path:
        return path
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return os.path.abspath(path)


def open_file(path, mode='r'):
    path = abspath(path)
    return codecs.open(path, mode, 'utf-8')


def get_file_data(path):
    return open_file(path).read()


def open_resource(path, mode='r'):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    path = os.path.join(dir_path, path)
    return open_file(path, mode)


def get_resource_data(path):
    return open_resource(path).read()


def conv_bool(obj):
    if isinstance(obj, basestring):
        return True if obj.lower() == 'true' else False
    return bool(obj)


def conv_list(obj, sep=','):
    if obj is None:
        return []
    obj = obj if obj else []
    obj = obj if isinstance(obj, list) else [obj]
    if not sep:
        return obj
    return [s.strip() for s in sep.join(obj).split(sep) if s.strip()]


def conv_lower(obj):
    if obj is None:
        return ''
    if isinstance(obj, basestring):
        return obj.lower()
    return obj
