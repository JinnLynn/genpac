# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

import sys

PY2 = sys.version_info[0] == 2

if PY2:
    string_types = basestring
    binary_type = str
    text_type = unicode

    def comfirm(prompt):
        return raw_input(prompt.encode('utf-8'))

    def iterkeys(d):
        return d.iterkeys()

    def itervalues(d):
        return d.itervalues()

    def iteritems(d):
        return d.iteritems()

    from os import getcwdu as getcwd
    import ConfigParser as configparser
    from StringIO import StringIO
    from urllib2 import build_opener
    from urllib import unquote
    from urlparse import urlparse

else:
    string_types = str
    binary_type = bytes
    text_type = str

    def comfirm(prompt):
        return input(prompt)

    def iterkeys(d):
        return iter(d.keys())

    def itervalues(d):
        return iter(d.values())

    def iteritems(d):
        return iter(d.items())

    from os import getcwd
    import configparser
    from io import StringIO
    from urllib.request import build_opener
    from urllib.parse import unquote, urlparse
