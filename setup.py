from setuptools import setup

long_description = '''
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


def get_version():
    with open('genpac/core.py') as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])

setup(
    name='genpac',
    version=get_version(),
    description='convert gfwlist to pac, custom rules supported.',
    long_description=long_description,
    author='JinnLynn',
    author_email='eatfishlin@gmail.com',
    url='https://github.com/JinnLynn/genpac',
    packages=['genpac', 'genpac.pysocks', 'genpac.publicsuffix'],
    package_data={
        'genpac': ['res/*']
    },
    entry_points={
        'console_scripts': [
            'genpac=genpac:main'
        ]
    },
    license='MIT',
    keywords='proxy pac gfwlist gfw',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
