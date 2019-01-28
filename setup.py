'''
|pypi version| |pypi license| |travis ci|

Generate PAC file from gfwlist, custom rules supported.

For more information, please visit `project page`_.


.. |pypi version| image:: https://img.shields.io/pypi/v/genpac.svg
   :target: https://pypi.python.org/pypi/genpac
.. |pypi license| image:: https://img.shields.io/pypi/l/genpac.svg
   :target: https://pypi.python.org/pypi/genpac
.. |travis ci| image:: https://img.shields.io/travis/JinnLynn/genpac.svg
   :target: https://travis-ci.org/JinnLynn/genpac

.. _project page: https://github.com/JinnLynn/genpac/
'''
import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('genpac/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


setup(
    name='genpac',
    version=version,
    license='MIT',
    author='JinnLynn',
    author_email='eatfishlin@gmail.com',
    url='https://github.com/JinnLynn/genpac',
    keywords='proxy pac gfwlist gfw',
    description='convert gfwlist to pac, custom rules supported.',
    long_description=__doc__,
    packages=['genpac'],
    package_data={
        'genpac': ['res/*'],
    },
    entry_points={
        'console_scripts': [
            'genpac=genpac:run'
        ]
    },
    platforms='any',
    install_requires=[
        'PySocks',
        'publicsuffixlist'
    ],
    extras_require={
        'testing': ['flake8', 'pytest', 'pytest-cov']
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
