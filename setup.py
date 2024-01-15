import sys

from setuptools import setup

setup(
    entry_points={
        "console_scripts": [
            "pip=pip._internal.cli.main:main",
            f"pip{sys.version_info[0]}=pip._internal.cli.main:main",
            "pip{}.{}=pip._internal.cli.main:main".format(*sys.version_info[:2]),
        ],
    },
)
