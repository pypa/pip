import os
from setuptools import setup, find_packages

HERE = os.path.dirname(__file__)
INDEX = "file://" + os.path.join(HERE, '..', '..', 'indexes', 'simple', 'simple')

setup(
    name='LocalExtras',
    version='0.0.1',
    packages=find_packages(),
    extras_require={ 'bar': ['simple'] },
    dependency_links=[INDEX]
)
