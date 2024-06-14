import os
from os import getcwd
import sys
import codecs
import re
import logging
import base64
import tempfile
from urllib.parse import unquote, urlparse
import argparse
import hashlib
import json
from importlib import metadata

from publicsuffixlist import PublicSuffixList

logger = logging.getLogger(__name__.split('.')[0])
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler(stream=sys.stderr)
sh.setFormatter(logging.Formatter(
                fmt='%(asctime)s[%(levelname)s]: %(message)s'))
logger.addHandler(sh)


_PSL = None


class Namespace(argparse.Namespace):
    def __init__(self, **kwargs):
        self.update(**kwargs)

    def update(self, **kwargs):
        keys = [k.strip().replace('-', '_') for k in kwargs.keys()]
        self.__dict__.update(**dict(zip(keys, kwargs.values())))

    def dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FatalError(Error):
    pass


class FatalIOError(FatalError):
    pass


def get_version():
    return metadata.version('genpac')


def get_project_url():
    for item in metadata.metadata('genpac').get_all('Project-URL'):
        d = item.split(',')
        try:
            if d[0].strip().lower() == 'homepage':
                return d[1].strip()
        except Exception:
            pass
    raise ValueError('Project URL missing.')


def surmise_domain(rule, subdomain=True):
    global _PSL
    _PSL = _PSL or PublicSuffixList(accept_unknown=False, only_icann=True)

    def _clear_asterisk(rule):
        if rule.find('*') < 0:
            return rule
        rule = rule.strip('*')
        rule = rule.replace('/*.', '/')
        rule = re.sub(r'/([a-zA-Z0-9]+)\*\.', '/', rule)
        rule = re.sub(r'\*([a-zA-Z0-9_%]+)', '', rule)
        rule = re.sub(r'^([a-zA-Z0-9_%]+)\*', '', rule)
        return rule

    domain = ''

    rule = _clear_asterisk(rule)
    rule = rule.lstrip('.')

    if rule.find('%2F') >= 0:
        rule = unquote(rule)

    if rule.startswith('http:') or rule.startswith('https:'):
        r = urlparse(rule)
        domain = r.hostname
    elif rule.find('/') > 0:
        r = urlparse('http://' + rule)
        domain = r.hostname
    elif rule.find('.') > 0:
        domain = rule

    if not subdomain:
        return _PSL.privatesuffix(domain)

    parts = _PSL.privateparts(domain)
    return '.'.join(parts) if parts else None


def error(*args, **kwargs):
    logger.error(*args)
    if kwargs.get('exit', False):
        sys.exit(kwargs.get('exit_code') or 1)


def exit_error(*args, **kwargs):
    error(*args, exit=True, exit_code=kwargs.get('code') or 1)


def exit_success(*args):
    logger.info(*args)
    sys.exit()


def b64encode(data, newline=True):
    if isinstance(data, str):
        data = data.encode()
    encoded = base64.encodebytes(data) if newline else base64.b64encode(data)
    return encoded.decode()


def b64decode(s):
    return base64.b64decode(s).decode()


def abspath(path, base=None):
    base = base or getcwd()
    if not path:
        return base
    path = os.path.expandvars(os.path.expanduser(path))
    return os.path.normpath(os.path.join(base, path))


def open_file(path, mode='r'):
    path = abspath(path)
    return codecs.open(path, mode, 'utf-8')


def read_file(path, fail_msg='读取文件{path}失败: {error}'):
    try:
        with open_file(path) as fp:
            return fp.read()
    except Exception as e:
        raise FatalIOError(fail_msg.format(**{'path': path, 'error': e}))


def write_file(path, content, fail_msg='写入文件{path}失败: {error}'):
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    try:
        with open_file(path, 'w') as fp:
            fp.write(content)
    except Exception as e:
        raise FatalError(fail_msg.format(**{'path': path, 'error': e}))


def remove_file(path, error_raise=True):
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        if error_raise:
            raise FatalIOError(f'remove file fail: {e} {path}')
    return False


def get_resource_path(path):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    return os.path.join(dir_path, path)


def open_resource(path, mode='r'):
    path = get_resource_path(path)
    return open_file(path, mode)


def get_resource_data(path):
    with open_resource(path) as fp:
        return fp.read()


def replace_all(text, replacements, **kwargs):
    def one_xlat(match):
        return replacements[match.group(0)]

    if not replacements and not kwargs:
        return text

    replacements = replacements or {}
    replacements.update(**kwargs)
    replacements = {k: str(v) for k, v in replacements.items()}

    rx = re.compile('|'.join(map(re.escape, replacements)))
    return rx.sub(one_xlat, text)


def conv_bool(obj):
    if isinstance(obj, str):
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
    if isinstance(obj, str):
        return obj.lower()
    return obj


def conv_path(obj):
    if isinstance(obj, str):
        return abspath(obj)
    if isinstance(obj, list):
        return [abspath(p) for p in obj]
    return obj


def mktemp(ext=None):
    if ext is not None:
        ext = str(ext).strip('.')
    suffix = f'.{ext}' if ext else None
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    return tmp.name


def get_cache_file(name):
    hash_ = calc_hash(name)
    dst_dir = os.path.join(tempfile.gettempdir(), 'genpac')
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    basename = os.path.join(dst_dir, hash_)
    return f'{basename}.json', f'{basename}.data'


def remove_cache_file(name):
    f_info, f_data = get_cache_file(name)
    remove_file(f_info, error_raise=False)
    remove_file(f_data, error_raise=False)


def calc_hash(content):
    m = hashlib.md5()
    m.update(content.encode())
    return m.hexdigest()


def hash_dict(d):
    if not d:
        return 'none'
    if not isinstance(d, dict):
        raise ValueError()
    return calc_hash(json.dumps(d, sort_keys=True))
