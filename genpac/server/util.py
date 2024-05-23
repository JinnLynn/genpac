import hashlib
from json import dumps


def calc_hash(content):
    m = hashlib.md5()
    m.update(content.encode())
    return m.hexdigest()


def hash_dict(d):
    if not d:
        return 'none'
    if not isinstance(d, dict):
        raise ValueError()
    return calc_hash(dumps(d, sort_keys=True))
