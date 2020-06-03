"""Convenient parallelization of higher order functions.

This module provides proper fallback functions for multiprocess
and multithread map, both the non-lazy, ordered variant
and the lazy, unordered variant.
"""

__all__ = ['map_multiprocess', 'imap_multiprocess',
           'map_multithread', 'imap_multithread']

from contextlib import contextmanager
from multiprocessing import Pool as ProcessPool
from multiprocessing.dummy import Pool as ThreadPool

from pip._vendor.requests.adapters import DEFAULT_POOLSIZE
from pip._vendor.six import PY2
from pip._vendor.six.moves import map

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import (
        Callable, Iterable, Iterator, List, Optional, Union, TypeVar)
    from multiprocessing import pool

    Pool = Union[pool.Pool, pool.ThreadPool]
    S = TypeVar('S')
    T = TypeVar('T')

# On platforms without sem_open, multiprocessing[.dummy] Pool
# cannot be created.
try:
    import multiprocessing.synchronize  # noqa
except ImportError:
    LACK_SEM_OPEN = True
else:
    LACK_SEM_OPEN = False

# Incredibly large timeout to work around bpo-8296 on Python 2.
TIMEOUT = 2000000


@contextmanager
def closing(pool):
    # type: (Pool) -> Iterator[Pool]
    """Return a context manager that closes and joins pool.

    This is needed for Pool.imap* to make the result iterator iterate.
    """
    try:
        yield pool
    finally:
        pool.close()
        pool.join()


def _map_fallback(func, iterable, chunksize=None):
    # type: (Callable[[S], T], Iterable[S], Optional[int]) -> List[T]
    """Return a list of func applied to each element in iterable.

    This function is the sequential fallback when sem_open is unavailable.
    """
    return list(map(func, iterable))


def _imap_fallback(func, iterable, chunksize=1):
    # type: (Callable[[S], T], Iterable[S], int) -> Iterator[T]
    """Make an iterator applying func to each element in iterable.

    This function is the sequential fallback when sem_open is unavailable.
    """
    return map(func, iterable)


def _map_multiprocess_py2(func, iterable, chunksize=None):
    # type: (Callable[[S], T], Iterable[S], Optional[int]) -> List[T]
    """Chop iterable into chunks and submit them to a process pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Note that this function may cause high memory usage
    for long iterables.

    Return a list of results in order.
    """
    pool = ProcessPool()
    try:
        return pool.map_async(func, iterable, chunksize).get(TIMEOUT)
    finally:
        pool.terminate()


def _map_multiprocess_py3(func, iterable, chunksize=None):
    # type: (Callable[[S], T], Iterable[S], Optional[int]) -> List[T]
    """Chop iterable into chunks and submit them to a process pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Note that this function may cause high memory usage
    for long iterables.

    Return a list of results in order.
    """
    with ProcessPool() as pool:
        return pool.map(func, iterable, chunksize)


def _imap_multiprocess_py2(func, iterable, chunksize=1):
    # type: (Callable[[S], T], Iterable[S], int) -> Iterator[T]
    """Chop iterable into chunks and submit them to a process pool.

    For very long iterables using a large value for chunksize can make
    the job complete much faster than using the default value of 1.

    Return an unordered iterator of the results.
    """
    pool = ProcessPool()
    try:
        return iter(pool.map_async(func, iterable, chunksize).get(TIMEOUT))
    finally:
        pool.terminate()


def _imap_multiprocess_py3(func, iterable, chunksize=1):
    # type: (Callable[[S], T], Iterable[S], int) -> Iterator[T]
    """Chop iterable into chunks and submit them to a process pool.

    For very long iterables using a large value for chunksize can make
    the job complete much faster than using the default value of 1.

    Return an unordered iterator of the results.
    """
    with ProcessPool() as pool, closing(pool):
        return pool.imap_unordered(func, iterable, chunksize)


def _map_multithread_py2(func, iterable, chunksize=None):
    # type: (Callable[[S], T], Iterable[S], Optional[int]) -> List[T]
    """Chop iterable into chunks and submit them to a thread pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Note that this function may cause high memory usage
    for long iterables.

    Return a list of results in order.
    """
    pool = ThreadPool(DEFAULT_POOLSIZE)
    try:
        return pool.map_async(func, iterable, chunksize).get(TIMEOUT)
    finally:
        pool.terminate()


def _map_multithread_py3(func, iterable, chunksize=None):
    # type: (Callable[[S], T], Iterable[S], Optional[int]) -> List[T]
    """Chop iterable into chunks and submit them to a thread pool.

    The (approximate) size of these chunks can be specified
    by setting chunksize to a positive integer.

    Note that this function may cause high memory usage
    for long iterables.

    Return a list of results in order.
    """
    with ThreadPool(DEFAULT_POOLSIZE) as pool:
        return pool.map(func, iterable, chunksize)


def _imap_multithread_py2(func, iterable, chunksize=1):
    # type: (Callable[[S], T], Iterable[S], int) -> Iterator[T]
    """Chop iterable into chunks and submit them to a thread pool.

    For very long iterables using a large value for chunksize can make
    the job complete much faster than using the default value of 1.

    Return an unordered iterator of the results.
    """
    pool = ThreadPool(DEFAULT_POOLSIZE)
    try:
        return pool.map_async(func, iterable, chunksize).get(TIMEOUT)
    finally:
        pool.terminate()


def _imap_multithread_py3(func, iterable, chunksize=1):
    # type: (Callable[[S], T], Iterable[S], int) -> Iterator[T]
    """Chop iterable into chunks and submit them to a thread pool.

    For very long iterables using a large value for chunksize can make
    the job complete much faster than using the default value of 1.

    Return an unordered iterator of the results.
    """
    with ThreadPool(DEFAULT_POOLSIZE) as pool, closing(pool):
        return pool.imap_unordered(func, iterable, chunksize)


if LACK_SEM_OPEN:
    map_multiprocess = map_multithread = _map_fallback
    imap_multiprocess = imap_multithread = _imap_fallback
elif PY2:
    map_multiprocess = _map_multiprocess_py2
    imap_multiprocess = _imap_multiprocess_py2
    map_multithread = _map_multithread_py2
    imap_multithread = _imap_multithread_py2
else:
    map_multiprocess = _map_multiprocess_py3
    imap_multiprocess = _imap_multiprocess_py3
    map_multithread = _map_multithread_py3
    imap_multithread = _imap_multithread_py3
