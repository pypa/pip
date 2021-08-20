#!/usr/bin/env python
from setuptools import setup

# ensure dependencies are installed
import simple
import simplewheel

assert simplewheel.__version__ == "2.0"

setup(
    name="pep518_with_extra_and_markers",
    version="1.0",
    py_modules=["pep518_with_extra_and_markers"],
)
