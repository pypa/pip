#!/usr/bin/env python
from setuptools import find_packages, setup

import simple  # ensure dependency is installed

setup(name='pep518',
      version='3.0',
      packages=find_packages()
      )
