#!/usr/bin/env python
from setuptools import find_packages, setup

import simple  # Test gh-4647 regression

setup(name='pep518',
      version='3.0',
      packages=find_packages()
      )
