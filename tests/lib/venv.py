from __future__ import absolute_import

import os
import sys

import virtualenv as _virtualenv

from .path import Path


class VirtualEnvironment(object):
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(self, location, wheel_dir, system_site_packages=False):
        self.location = Path(location)
        self.wheel_dir = wheel_dir
        self._system_site_packages = system_site_packages

        home, lib, inc, bin = _virtualenv.path_locations(self.location)
        # workaround for https://github.com/pypa/virtualenv/issues/306
        if hasattr(sys, "pypy_version_info"):
            lib = os.path.join(home, 'lib-python', sys.version[:3])
        self.lib = Path(lib)
        self.bin = Path(bin)

    def __repr__(self):
        return "<VirtualEnvironment {}>".format(self.location)

    @classmethod
    def create(cls, location, clear=False, wheel_dir=None):
        obj = cls(location, wheel_dir=wheel_dir)
        obj._create(clear=clear)
        return obj

    def _create(self, clear=False):
        # Create the actual virtual environment
        _virtualenv.create_environment(
            self.location,
            clear=clear,
            never_download=True,
            no_setuptools=True,
            no_pip=True,
        )

        # Install our development version of pip install the virtual
        # environment
        _virtualenv.install_wheel(
            ["setuptools", "pip"],
            self.bin.join("python"),
            [self.wheel_dir] + _virtualenv.file_search_dirs(),
        )

    def clear(self):
        self._create(clear=True)

    @property
    def system_site_packages(self):
        return self._system_site_packages

    @system_site_packages.setter
    def system_site_packages(self, value):
        marker = self.lib.join("no-global-site-packages.txt")
        if value:
            marker.rm()
        else:
            marker.touch()
        self._system_site_packages = value
