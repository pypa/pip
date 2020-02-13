# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

import ast
import codecs
import os
import sys

from setuptools import find_packages, setup


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def extract_global_vars(t):
    m = ast.parse(t)
    res = {}
    for s in m.body:
        if isinstance(s, ast.Assign):
            vo = s.value
            v = None
            if isinstance(vo, ast.Str):
                v = vo.s
            elif isinstance(vo, ast.Num):
                v = vo.n
            
            if v is not None:
                for t in s.targets:
                    if isinstance(t, ast.Name):
                        res[t.id] = v
    return res


def get_version(rel_path):
    return extract_global_vars(read(rel_path))['__version__']


long_description = read('README.rst')

setup(
    name="pip",
    version=get_version("src/pip/__init__.py"),
    description="The PyPA recommended tool for installing Python packages.",
    long_description=long_description,

    license='MIT',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    url='https://pip.pypa.io/',
    keywords='distutils easy_install egg setuptools wheel virtualenv',
    project_urls={
        "Documentation": "https://pip.pypa.io",
        "Source": "https://github.com/pypa/pip",
    },

    author='The pip developers',
    author_email='pypa-dev@groups.google.com',

    package_dir={"": "src"},
    packages=find_packages(
        where="src",
        exclude=["contrib", "docs", "tests*", "tasks"],
    ),
    package_data={
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": ["t32.exe", "t64.exe", "w32.exe", "w64.exe"],
    },
    entry_points={
        "console_scripts": [
            "pip=pip._internal.cli.main:main",
            "pip{}=pip._internal.cli.main:main".format(sys.version_info[0]),
            "pip{}.{}=pip._internal.cli.main:main".format(
                *sys.version_info[:2]
            ),
        ],
    },

    zip_safe=False,
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*',
)
