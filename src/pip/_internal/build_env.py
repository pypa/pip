"""Build Environment used for isolation during sdist building
"""

import os
from sysconfig import get_paths

from pip._internal.utils.temp_dir import TempDirectory


class BuildEnvironment(object):
    """Manages a temporary environment to install build deps
    """

    def __init__(self, no_clean):
        self._temp_dir = TempDirectory(kind="build-env")
        self._no_clean = no_clean

    @property
    def path(self):
        return self._temp_dir.path

    def __enter__(self):
        self._temp_dir.create()

        self.save_path = os.environ.get('PATH', None)
        self.save_pythonpath = os.environ.get('PYTHONPATH', None)

        install_scheme = 'nt' if (os.name == 'nt') else 'posix_prefix'
        install_dirs = get_paths(install_scheme, vars={
            'base': self.path,
            'platbase': self.path,
        })

        scripts = install_dirs['scripts']
        if self.save_path:
            os.environ['PATH'] = scripts + os.pathsep + self.save_path
        else:
            os.environ['PATH'] = scripts + os.pathsep + os.defpath

        if install_dirs['purelib'] == install_dirs['platlib']:
            lib_dirs = install_dirs['purelib']
        else:
            lib_dirs = install_dirs['purelib'] + os.pathsep + \
                install_dirs['platlib']
        if self.save_pythonpath:
            os.environ['PYTHONPATH'] = lib_dirs + os.pathsep + \
                self.save_pythonpath
        else:
            os.environ['PYTHONPATH'] = lib_dirs

        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._no_clean:
            self._temp_dir.cleanup()
        if self.save_path is None:
            os.environ.pop('PATH', None)
        else:
            os.environ['PATH'] = self.save_path

        if self.save_pythonpath is None:
            os.environ.pop('PYTHONPATH', None)
        else:
            os.environ['PYTHONPATH'] = self.save_pythonpath
