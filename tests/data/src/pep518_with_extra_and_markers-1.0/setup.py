#!/usr/bin/env python
import sys

from setuptools import setup

# ensure dependencies are installed
import simple
import simplewheel

assert simplewheel.__version__ == '1.0' if sys.version_info < (3,) else '2.0'

setup(name='pep518_with_extra_and_markers',
      version='1.0',
      py_modules=['pep518_with_extra_and_markers'],
      )
