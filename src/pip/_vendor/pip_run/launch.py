import textwrap
import os
import subprocess
import sys
import signal
import glob
import itertools


class PathReader:
    @staticmethod
    def _read_file(filename):
        root = os.path.dirname(filename)
        return (
            os.path.join(root, path.rstrip())
            for path in open(filename)
            if path.strip()
            and not path.startswith('#')
            and not path.startswith('import ')
        )

    @classmethod
    def _read(cls, target):
        """
        As .pth files aren't honored except in site dirs,
        read the paths indicated by them.
        """
        pth_files = glob.glob(os.path.join(target, '*.pth'))
        file_items = map(cls._read_file, pth_files)
        return itertools.chain.from_iterable(file_items)


def _inject_sitecustomize(target):
    """
    Create a sitecustomize file in the target that will install
    the target as a sitedir.
    """
    hook = (
        textwrap.dedent(
            """
        import site
        site.addsitedir({target!r})
        """
        )
        .lstrip()
        .format(**locals())
    )
    sc_fn = os.path.join(target, 'sitecustomize.py')
    with open(sc_fn, 'w') as strm:
        strm.write(hook)


def _pythonpath():
    return 'JYTHONPATH' if sys.platform.startswith('java') else 'PYTHONPATH'


def _build_env(target):
    """
    Prepend target and .pth references in target to PYTHONPATH
    """
    key = _pythonpath()
    env = dict(os.environ)
    suffix = env.get(key)
    prefix = (target,)
    items = itertools.chain(
        prefix, PathReader._read(target), (suffix,) if suffix else ()
    )
    joined = os.pathsep.join(items)
    env[key] = joined
    return env


def _setup_env(target):
    _inject_sitecustomize(target)
    return _build_env(target)


def with_path(target, params):
    """
    Launch Python with target on the path and params
    """

    def null_handler(signum, frame):
        pass

    signal.signal(signal.SIGINT, null_handler)
    cmd = [sys.executable] + params
    return subprocess.Popen(cmd, env=_setup_env(target)).wait()


def with_path_overlay(target, params):
    """
    Overlay Python with target on the path and params
    """
    cmd = [sys.executable] + params
    os.execve(sys.executable, cmd, _setup_env(target))
