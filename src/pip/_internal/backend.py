import ast
import importlib
import logging
import os
import sys
import tempfile
import textwrap
import platform

from pip._internal.utils.misc import call_subprocess, ensure_dir
from pip._internal.utils.setuptools_build import SETUPTOOLS_SHIM
from pip._internal.utils.temp_dir import TempDirectory

from sysconfig import get_paths
from copy import copy

logger = logging.getLogger(__name__)


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
        if platform.python_implementation() == 'PyPy':
            command_base += ['-S', '-s']
        elif sys.version_info < (3, 4):
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
