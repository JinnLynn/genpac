from os import path
import glob
import importlib

from .base import FmtBase, formater

__all__ = ['FmtBase', 'formater']


def _import_all_format():
    for f in glob.glob(path.join(path.dirname(__file__), "*.py")):
        f_bn = path.basename(f)
        if not path.isfile(f) or f_bn in ['__init__.py', 'base.py']:
            continue
        importlib.import_module(f'.{f_bn[:-3]}', __package__)


_import_all_format()
del _import_all_format
