# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import sys
import codecs


def error(*args, **kwargs):
    print(*args, file=sys.stderr)
    if kwargs.get('exit', False):
        sys.exit(kwargs.get('exit_code') or 1)


def exit_error(*args, **kwargs):
    error(*args, exit=True, exit_code=kwargs.get('code') or 1)


def exit_success(*args):
    print(*args)
    sys.exit()


def abspath(path):
    return os.path.abspath(os.path.expanduser(path)) if path else os.getcwd()


def open_file(path, mode='r'):
    path = abspath(path)
    return codecs.open(path, mode, 'utf-8')


def read_file(path, fail_exit=True,
              fail_msg='读取文件{path}失败: {error}'):
    error = None
    try:
        with open_file(path) as fp:
            return fp.read(), None
    except Exception as e:
        error = e

    if fail_exit:
        exit_error(fail_msg.format(**{'path': path, 'error': error or '未知'}))
    return None, error


def write_file(path, content,
               fail_exit=True, fail_msg='写入文件{path}失败: {error}'):
    error = None
    try:
        with open_file(path, 'w') as fp:
            fp.write(content)
        return True, None
    except Exception as e:
        error = e

    if fail_exit:
        exit_error(fail_msg.format(**{'path': path, 'error': error or '未知'}))
    return False, error


def get_resource_path(path):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    return os.path.join(dir_path, path)


def open_resource(path, mode='r'):
    path = get_resource_path(path)
    return open_file(path, mode)


def get_resource_data(path):
    return open_resource(path).read()


def conv_bool(obj):
    if isinstance(obj, basestring):
        return True if obj.lower() == 'true' else False
    return bool(obj)


def conv_list(obj, sep=','):
    obj = obj or ''
    if isinstance(obj, list):
        obj = '\n'.join(obj)
    obj = obj.replace(sep, '\n')
    return [s.strip() for s in obj.splitlines() if s.strip()]


def conv_lower(obj):
    obj = obj or ''
    if isinstance(obj, basestring):
        return obj.lower()
    return obj


def conv_path(obj):
    if isinstance(obj, basestring):
        return abspath(obj)
    if isinstance(obj, list):
        return [abspath(p) for p in obj]
    return obj
