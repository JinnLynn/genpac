# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import re
import os
from ConfigParser import MissingSectionHeaderError, ParsingError
import StringIO

from .util import open_file


class Config(object):
    _SECTCRE = re.compile(
        r'\['                                 # [
        r'(?P<header>[^]]+)'                  # very permissive!
        r'\]'                                 # ]
        )
    _OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?P<vi>[:=])\s*'                 # any number of space/tab,
                                              # followed by separator
                                              # (either : or =), followed
                                              # by any # space/tab
        r'(?P<value>.*)$'                     # everything up to eol
        )
    _OPTCRE_NV = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?:'                             # any number of space/tab,
        r'(?P<vi>[:=])\s*'                    # optionally followed by
                                              # separator (either : or
                                              # =), followed by any #
                                              # space/tab
        r'(?P<value>.*))?$'                   # everything up to eol
        )

    def __init__(self):
        super(Config, self).__init__()
        self._sections = {}
        self._section_uniques = {}
        self._optcre = self._OPTCRE

    def parse(self, filename):
        with open_file(filename) as fp:
            self.parsefp(fp)

    def parsefp(self, fp):
        try:
            filename = fp.name
        except AttributeError:
            filename = '<???>'
        # 展开形如${ENV}的变量
        content = os.path.expandvars(fp.read())
        self._parse(StringIO.StringIO(content), filename)

    def _options(self, section):
        if section not in self._sections:
            return {}
        opts = self._sections[section].copy()
        if '__name__' in opts:
            del opts['__name__']
        return opts

    def options(self, section, enable_repeat=False):
        if not enable_repeat:
            return self._options(section)

        if section not in self._sections:
            return []
        opts = [self._options(section)]
        for i in range(1, len(self._sections) + 1):
            sectname = section + '#' + str(i)
            opt = self._options(sectname)
            if not opt:
                break
            opts.append(opt)
        return opts

    def optionxform(self, optionstr):
        return optionstr.lower()

    def section_unique(self, sectname):
        if sectname in self._section_uniques:
            self._section_uniques[sectname] += 1
            return sectname + '#' + str(self._section_uniques[sectname])
        self._section_uniques[sectname] = 0
        return sectname

    def _parse(self, fp, fpname=None):
        cursect = None                        # None, or a dictionary
        optname = None
        lineno = 0
        e = None                              # None, or an exception

        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if not line.strip() or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                # print(value)
                if value:
                    cursect[optname].append(value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self._SECTCRE.match(line)
                if mo:
                    # sectname = mo.group('header')
                    # if sectname in sections:
                    #     cursect = sections[sectname]
                    # else:
                    #     cursect = {}
                    #     cursect['__name__'] = sectname
                    #     sections[sectname] = cursect
                    # # So sections can't start with a continuation line
                    # optname = None
                    sectname = mo.group('header')
                    sectname = self.section_unique(sectname)
                    cursect = {}
                    cursect['__name__'] = sectname
                    self._sections[sectname] = cursect
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        optname = self.optionxform(optname.rstrip())
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos - 1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                            # allow empty values
                            if optval == '""':
                                optval = ''
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

        for options in self._sections.values():
            for name, val in options.items():
                if isinstance(val, list):
                    options[name] = '\n'.join(val)
