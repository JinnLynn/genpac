# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '2.0a1'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2017 JinnLynn'
__all__ = ['gp', 'run']

from .core import gp


def run():
    gp.run()
