# import hashlib
# import random
# import string

# from .. import FatalError  # noqa: F401
# from ..util import logger  # noqa: F401


# def calc_hash(content):
#     m = hashlib.md5()
#     m.update(content.encode())
#     return m.hexdigest()


# def randstr(length=16):
#     return ''.join(random.sample(string.ascii_letters + string.digits, length))


# def log_and_raise(msg):
#     logger.error(msg)
#     raise FatalError(msg)
