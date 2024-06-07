import re
import os
from collections import OrderedDict
import configparser
from io import StringIO

from .util import open_file


class Config(object):
    _SECTCRE = re.compile(
        r'\['                                 # [
        r'(?P<header>[^]]+)'                  # very permissive!
        r'\]')                                # ]
    _OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?P<vi>[:=])\s*'                 # any number of space/tab,
                                              # followed by separator
                                              # (either : or =), followed
                                              # by any # space/tab
        r'(?P<value>.*)$')                    # everything up to eol
    _OPTCRE_NV = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?:'                             # any number of space/tab,
        r'(?P<vi>[:=])\s*'                    # optionally followed by
                                              # separator (either : or
                                              # =), followed by any #
                                              # space/tab
        r'(?P<value>.*))?$')                  # everything up to eol

    def __init__(self):
        self._sections = OrderedDict()
        self._section_uniques = {}
        self._optcre = self._OPTCRE

    def read(self, filename):
        with open_file(filename) as fp:
            self.readfp(fp)

    def readfp(self, fp):
        try:
            filename = fp.name
        except AttributeError:
            filename = '<???>'
        # 展开形如${ENV}的变量
        content = os.path.expandvars(fp.read())
        self._parse(StringIO(content), filename)

    def iteroptions(self, section, sub_section_key=None):
        for opt in self.sections(section, sub_section_key=sub_section_key):
            yield opt

    def section(self, name):
        return self._options(name)

    def sections(self, name, sub_section_key=None):
        sub_section_key = sub_section_key or '__SUB_SECTION__'
        opts = []
        for sec in self._sections:
            opt = self._options(sec)
            if sec.startswith(name + ':'):
                secs = sec.split(':', 1)
                try:
                    _, ss = secs
                    ss = ss.split('#')[0]
                except Exception:
                    _, ss = secs[0], None
                if sub_section_key not in opt:
                    opt[sub_section_key] = ss
            elif sec != name and not sec.startswith(name + '#'):
                continue
            opts.append(opt)
        return opts or []

    def _options(self, section):
        if section not in self._sections:
            return {}
        opts = self._sections[section].copy()
        if '__name__' in opts:
            del opts['__name__']
        return opts

    def _optionxform(self, optionstr):
        return optionstr.lower()

    def _section_unique(self, sectname):
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
                    sectname = mo.group('header')
                    sectname = self._section_unique(sectname)
                    cursect = {}
                    cursect['__name__'] = sectname
                    self._sections[sectname] = cursect
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise configparser.MissingSectionHeaderError(
                        fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        optname = self._optionxform(optname.rstrip())
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
                            e = configparser.ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

        for options in self._sections.values():
            for name, val in options.items():
                if isinstance(val, list):
                    options[name] = '\n'.join(val)
