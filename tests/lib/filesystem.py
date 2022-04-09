"""Helpers for filesystem-dependent tests.
"""
import os
from functools import partial
from itertools import chain
from typing import Iterator, List, Set


def get_filelist(base: str) -> Set[str]:
    def join(dirpath: str, dirnames: List[str], filenames: List[str]) -> Iterator[str]:
        relative_dirpath = os.path.relpath(dirpath, base)
        join_dirpath = partial(os.path.join, relative_dirpath)
        return chain(
            (join_dirpath(p) for p in dirnames),
            (join_dirpath(p) for p in filenames),
        )

    return set(chain.from_iterable(join(*dirinfo) for dirinfo in os.walk(base)))
