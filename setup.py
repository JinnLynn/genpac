from setuptools import setup

setup(
    name='genpac',
    version='1.1.0',
    description='convert gfwlist to pac, custom rules supported.',
    long_description=open('README.md', 'r').read(),
    author='JinnLynn',
    author_email='eatfishlin@gmail.com',
    url='https://github.com/JinnLynn/genpac',
    packages=['genpac', 'genpac.pysocks'],
    package_data={
        'genpac': ['res/*']
    },
    entry_points={
        'console_scripts': 'genpac=genpac:main'
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
