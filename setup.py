import codecs
import os
import re
import sys

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        version_file,
        re.M,
    )
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string.")


setup(
    # unfortunately we can't just use attr: src.pip.__version__ here
    version=find_version("src", "pip", "__init__.py"),
    package_data={
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": ["t32.exe", "t64.exe", "w32.exe", "w64.exe"],
    },
    entry_points={
        "console_scripts": [
            "pip=pip._internal:main",
            "pip%s=pip._internal:main" % sys.version_info[:1],
            "pip%s.%s=pip._internal:main" % sys.version_info[:2],
        ],
    },
)
