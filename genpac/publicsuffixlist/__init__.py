# -*- coding: utf-8 -*-
#
# Copyright 2014 ko-zu <causeless@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import os
import sys

__all__ = ["PublicSuffixList"]

ENCODING = "utf-8"

PSLURL = "https://publicsuffix.org/list/public_suffix_list.dat"

PSLFILE = os.path.join(os.path.dirname(__file__), "public_suffix_list.dat")

if sys.version_info >= (3, ):
    # python3.x
    def u(s):
        return s if isinstance(s, str) else s.decode(ENCODING)

    def b(s):
        return s if isinstance(s, bytes) else s.encode(ENCODING)
    basestr = str
    decodablestr = (str, bytes)

else:
    # python 2.x
    def u(s):
        return s if isinstance(s, unicode) else s.decode(ENCODING)
    def b(s):
        return s if isinstance(s, str) else s.encode(ENCODING)
    basestr = basestring
    decodablestr = basestring


def encode_idn(domain):
    return u(domain).encode("idna").decode("ascii")


def decode_idn(domain):
    return b(domain).decode("idna")


class PublicSuffixList(object):
    """ PublicSuffixList parser.

    After __init__(), all instance methods become thread-safe.
    Most methods accept str or unicode as input in Python 2.x, str (not bytes) in Python 3.x.
    """

    def __init__(self, source=None, accept_unknown=True, accept_encoded_idn=True,
                 only_icann=False):
        """ Parse PSL source file and Return PSL object

        source: file (line iterable) object, or flat str to parse. (Default: built-in PSL file)
        accept_unknown: bool, assume unknown TLDs to be public suffix. (Default: True)
        accept_encoded_idn: bool, if False, do not generate punycoded version of PSL.
            Without punycoded PSL object, parseing punycoded IDN cause incorrect results. (Default: True)
        only_icann: bool, if True, only ICANN suffixes are honored, not private ones.
            The markers '// ===BEGIN ICANN DOMAINS===' and '// ===END ICANN DOMAINS==='
            are needed for ICANN section detection. (Default: False)
        """

        self.accept_unknown = accept_unknown

        if source is None:
            try:
                source = open(PSLFILE, "rb")
                self._parse(source, accept_encoded_idn, only_icann=only_icann)
            finally:
                if source:
                    source.close()
        else:
            self._parse(source, accept_encoded_idn, only_icann=only_icann)

    def _parse(self, source, accept_encoded_idn, only_icann=False):
        """ PSL parser core """

        publicsuffix = set()
        maxlabel = 0
        section_is_icann = None

        if isinstance(source, decodablestr):
            source = source.splitlines()

        ln = 0
        for line in source:
            ln += 1
            if only_icann:
                ul = u(line).rstrip()
                if ul == "// ===BEGIN ICANN DOMAINS===":
                    section_is_icann = True
                    continue
                elif ul == "// ===END ICANN DOMAINS===":
                    section_is_icann = False
                    continue
                if not section_is_icann:
                    continue

            s = u(line).lower().split(" ")[0].rstrip()
            if s == "" or s.startswith("//"):
                continue

            maxlabel = max(maxlabel, s.count(".") + 1)
            publicsuffix.add(s)
            if accept_encoded_idn:
                e = encode_idn(s.lstrip("!"))
                if s[0] == "!":
                    publicsuffix.add("!" + e)
                else:
                    publicsuffix.add(e)

        self._publicsuffix = frozenset(publicsuffix)
        self._maxlabel = maxlabel

    def suffix(self, domain, accept_unknown=None):
        """ Alias for privatesuffix """
        return self.privatesuffix(domain, accept_unknown)

    def privatesuffix(self, domain, accept_unknown=None):
        """ Return shortest suffix assigned for an individual.

        domain: str or unicode to parse. (Required)
        accept_unknown: bool, assume unknown TLDs to be public suffix. (Default: object default)

        Return None if domain has invalid format.
        Return None if domain has no private part.
        """

        if accept_unknown is None:
            accept_unknown = self.accept_unknown

        if not isinstance(domain, basestr):
            raise TypeError()

        labels = domain.lower().rsplit(".", self._maxlabel + 2)
        ll = len(labels)

        if "\0" in domain or "" in labels:
            # not a valid domain
            return None

        if ll <= 1:
            # is TLD
            return None

        # skip labels longer than rules
        for i in range(max(0, ll - self._maxlabel), ll):
            s = ".".join(labels[i:])

            if i > 0 and ("!*." + s) in self._publicsuffix:
                return ".".join(labels[i-1:])

            if ("!" + s) in self._publicsuffix:
                # exact private match
                return s

            if i > 0 and ("*." + s) in self._publicsuffix:
                if i <= 1:
                    # domain is publicsuffix
                    return None
                else:
                    return ".".join(labels[i-2:])

            if s in self._publicsuffix:
                if i > 0:
                    return ".".join(labels[i-1:])
                else:
                    # domain is publicsuffix
                    return None

        else:
            # no match found
            if self.accept_unknown and ll >= 2:
                return ".".join(labels[-2:])
            else:
                return None

    def publicsuffix(self, domain, accept_unknown=None):
        """ Return longest publically shared suffix.

        domain: str or unicode to parse. (Required)
        accept_unknown: bool, assume unknown TLDs to be public suffix. (Default: object default)

        Return None if domain has invalid format.
        Return None if domain is not listed in PSL and accept_unknown is False.
        """

        if accept_unknown is None:
            accept_unknown = self.accept_unknown

        if not isinstance(domain, basestr):
            raise TypeError()

        labels = domain.lower().rsplit(".", self._maxlabel + 2)
        ll = len(labels)

        if "\0" in domain or "" in labels:
            # not a valid domain
            return None

        # shortcut for tld
        if ll == 1:
            if accept_unknown:
                return domain
            else:
                return None

        # skip labels longer than rules
        for i in range(max(0, ll - self._maxlabel), ll):
            s = ".".join(labels[i:])

            if i > 0 and ("!*." + s) in self._publicsuffix:
                return s

            if ("!" + s) in self._publicsuffix:
                # exact exclude
                if i + 1 < ll:
                    return ".".join(labels[i+1:])
                else:
                    return None

            if i > 0 and ("*." + s) in self._publicsuffix:
                return ".".join(labels[i-1:])

            if s in self._publicsuffix:
                return s

        else:
            # no match found
            if accept_unknown:
                return labels[-1]
            else:
                return None

    def is_private(self, domain):
        """ Return True if domain is private suffix or sub-domain. """
        return self.suffix(domain) is not None

    def is_public(self, domain):
        """ Return True if domain is publix suffix. """
        return self.publicsuffix(domain) == domain

    def privateparts(self, domain):
        """ Return tuple of labels and the private suffix. """
        s = self.privatesuffix(domain)
        if s is None:
            return None
        else:
            # I know the domain is valid and ends with private suffix
            pre = domain[0:-(len(s)+1)]
            if pre == "":
                return (s,)
            else:
                return tuple(pre.split(".") + [s])

    def subdomain(self, domain, depth):
        """ Return so-called subdomain of specified depth in the private suffix. """
        p = self.privateparts(domain)
        if p is None or depth > len(p) - 1:
            return None
        else:
            return ".".join(p[-(depth+1):])
