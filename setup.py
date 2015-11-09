import codecs
import os
import re
import shutil
import sys
import zipfile
import zipimport

from distutils.command.build_scripts import build_scripts
from distutils.command.install import install
from distutils.core import Command

import pkg_resources

from setuptools import Distribution as _Distribution, setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.easy_install import easy_install
from setuptools.command.test import test as TestCommand


# We want to ensure that our setup_requires items are ALWAYS installed unzipped
# and monkeypatching this will ensure that.
easy_install.should_unzip = lambda *a, **kw: True


here = os.path.abspath(os.path.dirname(__file__))


BUNDLED = [
    "distlib==0.2.1",
    "html5lib==1.0b5",
    "six==1.9.0",
    "colorama==0.3.3",
    "requests==2.7.0",
    "CacheControl==0.11.5",
    "lockfile==0.10.2",
    "progress==1.2",
    "ipaddress==1.0.14",  # Only needed on 2.6 and 2.7
    "packaging==15.3",
    "retrying==1.3.3",
    "setuptools==18.5",
]


MAIN_PY = """
import sys

from pip.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
""".lstrip()


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for filename in files:
            fullpath = os.path.join(root, filename)
            relpath = os.path.relpath(fullpath, path)
            ziph.write(fullpath, relpath)


class Distribution(_Distribution):

    def has_scripts(self):
        return True


class BuildDeps(Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        shutil.rmtree("build/deps", ignore_errors=True)

        try:
            os.makedirs("build/deps")
        except IOError:
            pass

        # Copy all of the bundled items into our build directory.
        for bundled in BUNDLED:
            dist = pkg_resources.get_distribution(bundled)
            assert not isinstance(dist.loader, zipimport.zipimporter), (
                "Cannot have a zip importer for {0!r}".format(dist)
            )

            top_level = dist.get_metadata("top_level.txt").split()

            for filename in os.listdir(dist.module_path):
                fullname = os.path.join(dist.module_path, filename)
                if os.path.isdir(fullname):
                    if filename not in top_level:
                        continue
                    shutil.copytree(
                        fullname,
                        os.path.join("build/deps", filename),
                        ignore=shutil.ignore_patterns("*.pyc"),
                    )
                elif os.path.isfile(fullname):
                    if os.path.splitext(filename)[0] not in top_level:
                        continue
                    shutil.copy2(
                        fullname,
                        os.path.join("build/deps", filename),
                    )


class BuildZipApp(Command):

    user_options = []

    sub_commands = [
        ("build_deps", None),
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Run all of our sub commands
        for cmd in self.get_sub_commands():
            self.run_command(cmd)

        # We need to run build_py, but we need to override some of it's
        # settings
        bpy = build_py(self.distribution)
        bpy.finalize_options()
        bpy.build_lib = "build/app"
        bpy.packages = find_packages(
            exclude=["contrib", "docs", "tests*", "tasks"],
        )
        bpy.run()

        with zipfile.ZipFile("build/pip", "w") as ziph:
            zipdir("build/deps", ziph)
            zipdir("build/app", ziph)
            ziph.writestr("__main__.py", MAIN_PY)

        with open("build/pip", "rb+") as f:
            content = f.read()
            f.seek(0, 0)
            f.write(b"#!python\n\n")
            f.write(content)


class BuildScript(build_scripts):

    def finalize_options(self):
        build_scripts.finalize_options(self)

        if self.scripts is None:
            self.scripts = []

        if self.distribution.scripts is None:
            self.distribution.scripts = []

    def run(self):
        self.run_command("build_zipapp")
        self.scripts.append("build/pip")
        self.distribution.scripts.append("build/pip")

        build_scripts.run(self)


class Install(install):

    sub_commands = [("install_egg_info", None)] + install.sub_commands


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

tests_require = ['pytest', 'virtualenv>=1.10', 'scripttest>=1.3', 'mock']


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
    setup_requires=BUNDLED,
    tests_require=tests_require,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    cmdclass={
        'build_deps': BuildDeps,
        'build_scripts': BuildScript,
        'build_zipapp': BuildZipApp,
        'install': Install,
        'test': PyTest,
    },
    distclass=Distribution,
)
