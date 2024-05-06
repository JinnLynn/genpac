__version__ = '3.0.dev7'
__author__ = 'JinnLynn <eatfishlin@gmail.com>'
__license__ = 'The MIT License'
__copyright__ = 'Copyright 2013-2023 JinnLynn'
__project_url__ = 'https://github.com/JinnLynn/genpac'

__all__ = ['GenPAC', 'Generator', 'TemplateFile', 'FmtBase',
           'formater', 'run', 'parse_rules']

from .core import GenPAC, Generator, run, parse_rules
from .template import TemplateFile
from .format.base import formater, FmtBase
from .deprecated import install_showwarning

install_showwarning()
