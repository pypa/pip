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


long_description = read("README.rst")

setup(
    name="pip",
    version=get_version("src/pip/__init__.py"),
    description="The PyPA recommended tool for installing Python packages.",
    long_description=long_description,
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    url="https://pip.pypa.io/",
    project_urls={
        "Documentation": "https://pip.pypa.io",
        "Source": "https://github.com/pypa/pip",
        "Changelog": "https://pip.pypa.io/en/stable/news/",
    },
    author="The pip developers",
    author_email="distutils-sig@python.org",
    package_dir={"": "src"},
    packages=find_packages(
        where="src",
        exclude=["contrib", "docs", "tests*", "tasks"],
    ),
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
    # NOTE: python_requires is duplicated in __pip-runner__.py.
    # When changing this value, please change the other copy as well.
    python_requires=">=3.7",
)
