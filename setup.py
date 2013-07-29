#! /usr/bin/env python
import os, sys
sys.path.insert(0, os.path.join((os.path.dirname(os.path.realpath(__file__))), "src"))

from setuptools import setup, find_packages

from genpac import __version__, __author__, __author_email__, __project_page__

setup(
    name            = 'genpac',
    version         = __version__,
    author          = __author__,
    author_email    = __author__,
    url             = __project_page__,
    license         = open('LICENSE', 'r').read(),
    description     = open('README.md', 'r').read(),
    keywords        = 'proxy pac gfwlist gfw',
    packages        = find_packages('src'),
    package_dir     = {'' : 'src'},
    zip_safe        = False,   
    entry_points    = {
        'console_scripts': 'genpac=genpac:main'}
)
