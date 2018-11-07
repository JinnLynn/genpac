# -*- coding: utf-8 -*-
#
# Copyright 2014 ko-zu <causeless@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from publicsuffixlist import PublicSuffixList as PSL

__all__ = ["PublicSuffixList"]


class PublicSuffixList(PSL):
    """ Drop in compatibility class to emulate publicsuffix module. """

    def get_public_suffix(self, domain):
        """ Return shortest private suffix or "". """

        return self.suffix(domain) or ""


class UnsafePublicSuffixList(PSL):
    """ More accurate compatibility class to emulate publicsuffix module. """

    def get_public_suffix(self, domain):
        """ Return shortest private suffix or longest public suffix. """

        return self.suffix(domain) or self.publicsuffix(domain) or ""
