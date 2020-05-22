"""Convenient parallelization of higher order functions."""

__all__ = ['map_multiprocess', 'map_multithread']

from multiprocessing import Pool as ProcessPool
from multiprocessing.dummy import Pool as ThreadPool

from pip._vendor.requests.adapters import DEFAULT_POOLSIZE
from pip._vendor.six.moves import map

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, Iterable, List, Optional, TypeVar

    S = TypeVar('S')
    T = TypeVar('T')


def map_multiprocess(func, iterable, chunksize=None, timeout=2000000):
    # type: (Callable[[S], T], Iterable[S], Optional[int], int) -> List[T]
    """Chop iterable into chunks and submit them to a process pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Block either until the results are ready and return them in a list
    or till timeout is reached.  By default timeout is an incredibly
    large number to work around bpo-8296 on Python 2.

    Note that it may cause high memory usage for long iterables.
    """
    try:
        pool = ProcessPool()
    except ImportError:
        return list(map(func, iterable))
    else:
        try:
            return pool.map_async(func, iterable, chunksize).get(timeout)
        finally:
            pool.terminate()


def map_multithread(func, iterable, chunksize=None, timeout=2000000):
    # type: (Callable[[S], T], Iterable[S], Optional[int], int) -> List[T]
    """Chop iterable into chunks and submit them to a thread pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Block either until the results are ready and return them in a list
    or till timeout is reached.  By default timeout is an incredibly
    large number to work around bpo-8296 on Python 2.

    Note that it may cause high memory usage for long iterables.
    """
    try:
        pool = ThreadPool(DEFAULT_POOLSIZE)
    except ImportError:
        return list(map(func, iterable))
    else:
        try:
            return pool.map_async(func, iterable, chunksize).get(timeout)
        finally:
            pool.terminate()
