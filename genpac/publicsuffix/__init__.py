# -*- coding: utf-8 -*-
# Copyright (c) 2015 nexB Inc.
# This code is based on Tomaž Šolc's fork of David Wilson's code originally at
# https://www.tablix.org/~avian/git/publicsuffix.git
#
# Copyright (c) 2014 Tomaž Šolc <tomaz.solc@tablix.org>
#
# David Wilson's code was originally at:
# from http://code.google.com/p/python-public-suffix-list/
#
# Copyright (c) 2009 David Wilson
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# The Public Suffix List vendored in this distribution has been downloaded
# from http://publicsuffix.org/public_suffix_list.dat
# This data file is licensed under the MPL-2.0 license.
# http://mozilla.org/MPL/2.0/

"""
Public Suffix List module for Python.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import sys
import codecs
from contextlib import closing
from datetime import datetime
import os.path

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

PY2 = sys.version_info[0] == 2
if PY2:
    string_types = basestring
else:
    string_types = str


BASE_DIR = os.path.dirname(__file__)
PSL_URL = 'https://publicsuffix.org/list/public_suffix_list.dat'
PSL_FILE = os.path.join(BASE_DIR, 'public_suffix_list.dat')
ABOUT_PSL_FILE = os.path.join(BASE_DIR, 'public_suffix_list.ABOUT')


def fetch():
    """
    Return a file-like object for the latest public suffix list downloaded from
    publicsuffix.org
    """
    req = Request(PSL_URL, headers={'User-Agent': 'python-publicsuffix2'})
    res = urlopen(req)
    try:
        encoding = res.headers.get_content_charset()
    except AttributeError:
        encoding = res.headers.getparam('charset')
    f = codecs.getreader(encoding)(res)
    return f


class PublicSuffixList(object):

    def __init__(self, psl_file=None):
        """
        Read and parse a public suffix list. `psl_file` is either a file
        location string, or a file-like object, or an iterable of lines from a
        public suffix data file.

        If psl_file is None, the vendored file named "public_suffix_list.dat" is
        loaded. It is stored side by side with this Python package.

        The file format is described at http://publicsuffix.org/
        """
        # Note: we test for None as we accept empty lists as inputs
        if psl_file is None or isinstance(psl_file, string_types):
            with codecs.open(psl_file or PSL_FILE, 'r', 'utf8') as psl:
                psl = psl.readlines()
        else:
            # assume file-like
            psl = psl_file
        root = self._build_structure(psl)
        self.root = self._simplify(root)

    def _find_node(self, parent, parts):
        if not parts:
            return parent

        if len(parent) == 1:
            parent.append({})

        assert len(parent) == 2
        _negate, children = parent

        child = parts.pop()

        child_node = children.get(child, None)

        if not child_node:
            children[child] = child_node = [0]

        return self._find_node(child_node, parts)

    def _add_rule(self, root, rule):
        if rule.startswith('!'):
            negate = 1
            rule = rule[1:]
        else:
            negate = 0

        parts = rule.split('.')
        self._find_node(root, parts)[0] = negate

    def _simplify(self, node):
        if len(node) == 1:
            return node[0]

        return (node[0], dict((k, self._simplify(v)) for (k, v) in node[1].items()))

    def _build_structure(self, fp):
        root = [0]

        for line in fp:
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            self._add_rule(root, line.split()[0].lstrip('.'))

        return root

    def _lookup_node(self, matches, depth, parent, parts):
        if parent in (0, 1):
            negate = parent
            children = None
        else:
            negate, children = parent

        matches[-depth] = negate

        if depth < len(parts) and children:
            for name in ('*', parts[-depth]):
                child = children.get(name, None)
                if child is not None:
                    self._lookup_node(matches, depth + 1, child, parts)

    def get_public_suffix(self, domain):
        """
        Return the public suffix for a `domain` DNS name.

        For example::
        >>> get_public_suffix("www.example.com")
            "example.com"

        Note that for internationalized domains the list at
        http://publicsuffix.org uses decoded names, so it is
        up to the caller to decode any Punycode-encoded names.
        """

        parts = domain.lower().strip('.').split('.')
        hits = [None] * len(parts)

        self._lookup_node(hits, 1, self.root, parts)

        for i, what in enumerate(hits):
            if what is not None and what == 0:
                return '.'.join(parts[i:])


_PSL = None


def get_public_suffix(domain, psl_file=None):
    """
    Return the public suffix for a `domain` DNS name.
    Convenience function that builds and caches a PublicSuffixList object.

    Optionally read, and parse a public suffix list. `psl_file` is either a file
    location string, or a file-like object, or an iterable of lines from a
    public suffix data file.

    If psl_file is None, the vendored file named "public_suffix_list.dat" is
    loaded. It is stored side by side with this Python package.

    The file format is described at http://publicsuffix.org/
    """
    global _PSL
    _PSL = _PSL or PublicSuffixList(psl_file)
    return _PSL.get_public_suffix(domain)
