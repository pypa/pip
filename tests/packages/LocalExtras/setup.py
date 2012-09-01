import os
from setuptools import setup, find_packages

HERE = os.path.dirname(__file__)
INDEX = os.path.join(HERE, '..', '..', 'in dex', 'FSPkg')

setup(
    name='LocalExtras',
    version='0.0.1',
    packages=find_packages(),
    extras_require={ 'bar': ['FSPkg'] },
    dependency_links=['file://' + INDEX]
)
