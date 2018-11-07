# -*- coding: utf-8 -*-
#
# Copyright 2014 ko-zu <causeless@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import os
import time
from email.utils import parsedate

from publicsuffixlist import PSLFILE, PSLURL, PublicSuffixList

try:
    import requests
except ImportError:
    requests = None


def updatePSL(psl_file=PSLFILE):
    """ Updates a local copy of PSL file

    :param psl_file: path for the file to store the list. Default: PSLFILE
    """
    if requests is None:
        raise Exception("Please install python-requests http(s) library. $ sudo pip install requests")


    r = requests.get(PSLURL)
    if r.status_code != requests.codes.ok or len(r.content) == 0:
        raise Exception("Could not download PSL from " + PSLURL)

    lastmod = r.headers.get("last-modified", None)
    f = open(psl_file + ".swp", "wb")
    f.write(r.content)
    f.close()

    with open(psl_file + ".swp", "rb") as f:
        psl = PublicSuffixList(f)

    os.rename(psl_file + ".swp", psl_file)
    if lastmod:
        t = time.mktime(parsedate(lastmod))
        os.utime(psl_file, (t, t))

    print("PSL updated")
    if lastmod:
        print("last-modified: " + lastmod)


if __name__ == "__main__":
    updatePSL()
