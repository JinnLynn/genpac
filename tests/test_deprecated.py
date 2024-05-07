# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import pytest

from genpac import run
from genpac.deprecated import GenPACDeprecationWarning
from tests.util import buildenv, join_etc
from tests.util import parametrize, xfail


@xfail(raises=SystemExit)
@parametrize('argv', [
    ['--gfwlist-disabled', '-c', join_etc('config-deprecated.ini')],
    '--gfwlist-disabled --format pac --proxy deprecated_proxy --compress --precise -o/dev/null',
    '--gfwlist-disabled --format pac -p deprecated_proxy -z -P -o/dev/null'])
def test_deprecated(argv):
    with buildenv(argv=argv):
        with pytest.warns(GenPACDeprecationWarning):
            run()
