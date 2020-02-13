# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

import codecs
import os
import sys

from setuptools import setup

__requires__ = ("setuptools >= 30.3.0", )


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            # __version__ = "0.9"
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    version=get_version("src/pip/__init__.py"),
    entry_points={
        "console_scripts": [
            "pip=pip._internal.cli.main:main",
            "pip{}=pip._internal.cli.main:main".format(sys.version_info[0]),
            "pip{}.{}=pip._internal.cli.main:main".format(
                *sys.version_info[:2]
            ),
        ],
    },
)
