__version__ = '3.0.dev6'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2023 JinnLynn'
__project_url__ = 'https://github.com/JinnLynn/genpac'

__all__ = ['GenPAC', 'TemplateFile', 'FmtBase',
           'formater', 'run', 'parse_rules']

from .core import GenPAC, Generator, Namespace, run, parse_rules
from .config import Config
from .template import TemplateFile
from .format import formater, FmtBase
from .util import surmise_domain
from .util import Error, FatalError, FatalIOError
from .deprecated import GenPACDeprecationWarning, install_showwarning

install_showwarning()
