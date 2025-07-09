"""Helpers for filesystem-dependent tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from itertools import chain
from pathlib import Path


def get_filelist(base: str) -> set[str]:
    def join(dirpath: str, dirnames: list[str], filenames: list[str]) -> Iterator[str]:
        relative_dirpath = os.path.relpath(dirpath, base)
        join_dirpath = partial(os.path.join, relative_dirpath)
        return chain(
            (join_dirpath(p) for p in dirnames),
            (join_dirpath(p) for p in filenames),
        )

    return set(chain.from_iterable(join(*dirinfo) for dirinfo in os.walk(base)))


@contextmanager
def chmod(path: str | Path, mode: int) -> Iterator[None]:
    """Contextmanager to temporarily update a path's mode."""
    old_mode = os.stat(path).st_mode
    try:
        os.chmod(path, mode)
        yield
    finally:
        os.chmod(path, old_mode)
