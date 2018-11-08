# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '2.1.0'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2018 JinnLynn'
__project_url__ = 'https://github.com/JinnLynn/genpac'

__all__ = ['GenPAC', 'TemplateFile', 'FmtBase',
           'formater', 'run', 'parse_rules']

from .core import GenPAC, Generator, Namespace, run, formater, parse_rules
from .config import Config
from .template import TemplateFile
from .formats import FmtBase
from .util import surmise_domain
from .util import Error, FatalError, FatalIOError
from .deprecated import GenPACDeprecationWarning, install_showwarning

install_showwarning()
