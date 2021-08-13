# A chatty setup.py for testing pip subprocess output handling

import os
import sys

from setuptools import setup

print(f"HELLO FROM CHATTYMODULE {sys.argv[1]}")
print(os.environ)
print(sys.argv)
if "--fail" in sys.argv:
    print("I DIE, I DIE")
    sys.exit(1)

setup(
    name="chattymodule",
    version="0.0.1",
    description="A sample Python project with a single module",
    py_modules=["chattymodule"],
)
