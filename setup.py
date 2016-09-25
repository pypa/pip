import codecs
import os
import re
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


here = os.path.abspath(os.path.dirname(__file__))


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest

        sys.exit(pytest.main(self.test_args))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

long_description = read('README.rst')

tests_require = ['pytest', 'virtualenv>=1.10', 'scripttest>=1.3', 'mock',
                 'pretend']


setup(
    name="pip",
    version=find_version("pip", "__init__.py"),
    description="The PyPA recommended tool for installing Python packages.",
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
    keywords='easy_install distutils setuptools egg virtualenv',
    author='The pip developers',
    author_email='python-virtualenv@groups.google.com',
    url='https://pip.pypa.io/',
    license='MIT',
    packages=find_packages(exclude=["contrib", "docs", "tests*", "tasks"]),
    package_data={
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": ["t32.exe", "t64.exe", "w32.exe", "w64.exe"],
    },
    entry_points={
        "console_scripts": [
            "pip=pip:main",
            "pip%s=pip:main" % sys.version[:1],
            "pip%s=pip:main" % sys.version[:3],
        ],
    },
    tests_require=tests_require,
    zip_safe=False,
    python_requires='>=2.6,!=3.0.*,!=3.1.*,!=3.2.*',
    extras_require={
        'testing': tests_require,
    },
    cmdclass={'test': PyTest},
)
