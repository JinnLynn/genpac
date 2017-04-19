# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '2.0a1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2017 JinnLynn'

__all__ = ['GenPAC', 'Namespace', 'formater', 'Config',
           'FmtBase', 'FmtPAC', 'FmtDnsmasq', 'FmtWingy',
           'run']

from .core import GenPAC, Namespace, formater
from .config import Config
from .formater import FmtBase, FmtPAC, FmtDnsmasq, FmtWingy


def run():
    gp = GenPAC()
    gp.run()
