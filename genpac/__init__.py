# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '2.0.0a1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2017 JinnLynn'

from .core import gp

__all__ = ['gp', 'run']


def run():
    gp.run()
