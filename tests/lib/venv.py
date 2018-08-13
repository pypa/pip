from __future__ import absolute_import

import distutils

import virtualenv as _virtualenv

from . import virtualenv_lib_path
from .path import Path


class VirtualEnvironment(object):
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(self, location, system_site_packages=False):
        self.location = Path(location)
        self._system_site_packages = system_site_packages
        home, lib, inc, bin = _virtualenv.path_locations(self.location)
        self.lib = Path(virtualenv_lib_path(home, lib))
        self.bin = Path(bin)

    def __repr__(self):
        return "<VirtualEnvironment {}>".format(self.location)

    @classmethod
    def create(cls, location, clear=False,
               pip_source_dir=None, relocatable=False):
        obj = cls(location)
        obj._create(clear=clear,
                    pip_source_dir=pip_source_dir,
                    relocatable=relocatable)
        return obj

    def _create(self, clear=False, pip_source_dir=None, relocatable=False):
        # Create the actual virtual environment
        _virtualenv.create_environment(
            self.location,
            clear=clear,
            download=False,
            no_pip=True,
            no_wheel=True,
        )
        _virtualenv.install_wheel([pip_source_dir or '.'],
                                  self.bin.join("python"))
        if relocatable:
            _virtualenv.make_environment_relocatable(self.location)
        # FIXME: some tests rely on 'easy-install.pth' being already present.
        site_package = distutils.sysconfig.get_python_lib(prefix=self.location)
        Path(site_package).join('easy-install.pth').touch()

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
