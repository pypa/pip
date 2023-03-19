import os
import sys

from setuptools import find_packages, setup


def read(rel_path: str) -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with open(os.path.join(here, rel_path)) as fp:
        return fp.read()


def get_version(rel_path: str) -> str:
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            # __version__ = "0.9"
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


setup(
    version=get_version("src/pip/__init__.py"),
    package_dir={"": "src"},
    packages=find_packages(
        where="src",
        exclude=["contrib", "docs", "tests*", "tasks"],
    ),
    include_package_data=False,
    package_data={
        "pip": ["py.typed"],
        "pip._vendor": ["vendor.txt"],
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": [
            "t32.exe",
            "t64.exe",
            "t64-arm.exe",
            "w32.exe",
            "w64.exe",
            "w64-arm.exe",
        ],
    },
    entry_points={
        "console_scripts": [
            "pip=pip._internal.cli.main:main",
            "pip{}=pip._internal.cli.main:main".format(sys.version_info[0]),
            "pip{}.{}=pip._internal.cli.main:main".format(*sys.version_info[:2]),
        ],
    },
    zip_safe=False,
)
