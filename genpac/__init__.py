# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '2.0b1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2017 JinnLynn'

__all__ = ['GenPAC', 'Namespace', 'Generator', 'formater', 'Config',
           'FmtBase', 'FmtPAC', 'FmtDnsmasq', 'FmtWingy',
           'GenPACDeprecationWarning', 'run']

from .core import GenPAC, Generator, Namespace, formater
from .config import Config
from .formats import FmtBase, FmtPAC, FmtDnsmasq, FmtWingy
from .deprecated import GenPACDeprecationWarning, install_showwarning

install_showwarning()


def run():
    gp = GenPAC()
    gp.run()
