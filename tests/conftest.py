# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import shutil
from pytest import fixture

from tests.util import join_etc, _TMP_DIR

@fixture(scope='session')
def config_file():
    return join_etc('config.ini')

@fixture(scope='session', autouse=True)
def clean_tmp():
    # print('clean_tmp')
    if os.path.exists(_TMP_DIR):
        shutil.rmtree(_TMP_DIR)
    os.makedirs(_TMP_DIR)
    yield
    # 用完后勿删除 node测试需要
    # print('clean_tmp over')
