import ast
import importlib
import logging
import os
import sys
import tempfile
import textwrap

from pip._internal.utils.misc import call_subprocess, ensure_dir
from pip._internal.utils.setuptools_build import SETUPTOOLS_SHIM
from pip._internal.utils.temp_dir import TempDirectory
from pip._vendor.six import PY2

from sysconfig import get_paths
from copy import copy

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
        self.cwd = os.path.abspath(cwd)
        self.backend_name = backend_name
        self.env = env
        
    def _log_debug_info(self, worker_name):
        logger.debug(textwrap.dedent("""
            {} runner data:
                Current Directory: {}
                System Backend: {}
                System Path: {}
                System Environment: {}
            """).format(
            worker_name,
            self.cwd,
            self.backend_name,
            sys.path,
            os.environ))


class BuildBackend(BuildBackendBase):
    """PEP 517 Build Backend"""
    def __init__(self, *args, **kwargs):
        super(BuildBackend, self).__init__(*args, **kwargs)
        self.env = dict(os.environ)

    def __getattr__(self, name):
        """Handles aribrary function invocations on the build backend."""
        def method(*args, **kw):
            self._log_debug_info('Parent')
            return BuildBackendCaller(
                self.cwd, self.env, self.backend_name)(name, *args, **kw)

        return method


class BuildBackendCaller(BuildBackendBase):
    def __call__(self, name, *args, **kwargs):
        """Handles aribrary function invocations on the build backend."""
        tmpf = tempfile.NamedTemporaryFile(delete=False)
        tmpf.close()
        command_base = [sys.executable]
        if PY2:
            command_base += ['-E', '-s']
        else:
            command_base += ['-I']
        try:
            call_subprocess(command_base + ['-c', textwrap.dedent(
                '''
                import importlib
                import os
                import sys

                py_path = {py_path!r}
                if py_path is not None:
                    sys.path[0:0] = py_path.split(os.pathsep)
                mod = importlib.import_module({backend_name!r})
                res = getattr(mod, {name!r})(*{args!r}, **{kwargs})
                with open({result!r}, 'w') as fp:
                    fp.write(repr(res))
                ''').format(
                    py_path=self.env.get('PYTHONPATH'),
                    backend_name=self.backend_name,
                    name=name, args=args, kwargs=kwargs,
                    result=tmpf.name,
                )], cwd=self.cwd, extra_environ=self.env, show_stdout=False)
            with open(tmpf.name) as fp:
                res = fp.read()
        finally:
            os.unlink(tmpf.name)
        return ast.literal_eval(res)
