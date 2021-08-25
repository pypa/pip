"""Helpers for filesystem-dependent tests.
"""
import os
import socket
import subprocess
import sys
from functools import partial
from itertools import chain
from typing import Iterator, List, Set

from .path import Path


def make_socket_file(path: str) -> None:
    # Socket paths are limited to 108 characters (sometimes less) so we
    # chdir before creating it and use a relative path name.
    cwd = os.getcwd()
    os.chdir(os.path.dirname(path))
    try:
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(os.path.basename(path))
    finally:
        os.chdir(cwd)


def make_unreadable_file(path: str) -> None:
    Path(path).touch()
    os.chmod(path, 0o000)
    if sys.platform == "win32":
        # Once we drop PY2 we can use `os.getlogin()` instead.
        username = os.environ["USERNAME"]
        # Remove "Read Data/List Directory" permission for current user, but
        # leave everything else.
        args = ["icacls", path, "/deny", username + ":(RD)"]
        subprocess.check_call(args)


def get_filelist(base: str) -> Set[str]:
    def join(dirpath: str, dirnames: List[str], filenames: List[str]) -> Iterator[str]:
        relative_dirpath = os.path.relpath(dirpath, base)
        join_dirpath = partial(os.path.join, relative_dirpath)
        return chain(
            (join_dirpath(p) for p in dirnames),
            (join_dirpath(p) for p in filenames),
        )

    return set(chain.from_iterable(join(*dirinfo) for dirinfo in os.walk(base)))
