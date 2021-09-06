"""This is a subpackage because the directory is on sys.path for _in_process.py

The subpackage should stay as empty as possible to avoid shadowing modules that
the backend might import.
"""
from os.path import dirname, abspath, join as pjoin
from contextlib import contextmanager

try:
    import importlib.resources as resources

    def _in_proc_script_path():
        if resources.is_resource(__package__, '_in_process.py'):
            return resources.path(__package__, '_in_process.py')
        return resources.path(__package__, '_in_process.pyc')
except ImportError:
    @contextmanager
    def _in_proc_script_path():
        _in_proc_script = pjoin(dirname(abspath(__file__)), '_in_process.py')
        if not os.path.isfile(_in_proc_script):
            _in_proc_script = pjoin(dirname(abspath(__file__)), '_in_process.pyc')
        yield _in_proc_script
