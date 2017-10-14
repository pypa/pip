import logging
import os
import sys
import importlib
import textwrap

from sysconfig import get_paths

from pip._internal.utils.misc import call_subprocess, ensure_dir
from pip._internal.utils.setuptools_build import SETUPTOOLS_SHIM
from pip._internal.utils.temp_dir import TempDirectory

from concurrent import futures


logger = logging.getLogger(__name__)


class BuildEnvironment(object):
    """Context manager to install build deps in a simple temporary environment
    """

    def __init__(self, no_clean):
        # TODO: Reuse build environment objects in the installation set
        self._temp_dir = TempDirectory(kind="build-env")
        self._no_clean = no_clean
        self._temp_dir_created = False

    def cleanup(self):
        return self._temp_dir.cleanup()

    def __enter__(self):
        if not self._temp_dir_created:
            self._temp_dir.create()
            self._temp_dir_created = True

        self.save_path = os.environ.get('PATH', None)
        self.save_pythonpath = os.environ.get('PYTHONPATH', None)

        install_scheme = 'nt' if (os.name == 'nt') else 'posix_prefix'
        install_dirs = get_paths(install_scheme, vars={
            'base': self._temp_dir.path,
            'platbase': self._temp_dir.path,
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

        return self._temp_dir.path

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



class BuildBackendBase(object):
    def __init__(self, cwd=None, env={}, backend_name='setuptools.build_meta'):
        self.cwd = cwd
        self.env = env
        self.backend_name = backend_name


class BuildBackend(BuildBackendBase):
    """PEP 517 Build Backend"""
    def __init__(self, *args, **kwargs):
        super(BuildBackend, self).__init__(*args, **kwargs)
        self.pool = futures.ProcessPoolExecutor()

    def __getattr__(self, name):
        """Handles aribrary function invocations on the build backend."""
        def method(*args, **kw):
            root = os.path.abspath(self.cwd)
            caller = BuildBackendCaller(root, self.env, self.backend_name)
            return self.pool.submit(caller, name, *args, **kw).result()

        return method


class BuildBackendCaller(BuildBackendBase):
    def __call__(self, name, *args, **kw):
        """Handles aribrary function invocations on the build backend."""
        os.chdir(self.cwd)
        os.environ.update(self.env)
        logger.debug(textwrap.dedent("""
            Subprocess runner data:
                Current Directory: {}
                System Backend: {}
                System Path: {}
                System Environment: {}
            """).format(
            self.cwd,
            self.backend_name,
            sys.path,
            os.environ))

        mod = importlib.import_module(self.backend_name)
        return getattr(mod, name)(*args, **kw)
