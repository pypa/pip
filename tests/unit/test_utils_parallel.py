"""Test multiprocessing/multithreading higher-order functions."""

from importlib import import_module
from math import factorial
from sys import modules

from pip._vendor.six import PY2
from pip._vendor.six.moves import map
from pytest import mark

DUNDER_IMPORT = '__builtin__.__import__' if PY2 else 'builtins.__import__'
FUNC, ITERABLE = factorial, range(42)
MAPS = ('map_multiprocess', 'imap_multiprocess',
        'map_multithread', 'imap_multithread')
_import = __import__


def reload_parallel():
    try:
        del modules['pip._internal.utils.parallel']
    finally:
        return import_module('pip._internal.utils.parallel')


def lack_sem_open(name, *args, **kwargs):
    """Raise ImportError on import of multiprocessing.synchronize."""
    if name.endswith('synchronize'):
        raise ImportError
    return _import(name, *args, **kwargs)


def have_sem_open(name, *args, **kwargs):
    """Make sure multiprocessing.synchronize import is successful."""
    if name.endswith('synchronize'):
        return
    return _import(name, *args, **kwargs)


@mark.parametrize('name', MAPS)
def test_lack_sem_open(name, monkeypatch):
    """Test fallback when sem_open is not available.

    If so, multiprocessing[.dummy].Pool will fail to be created and
    map_async should fallback to map.
    """
    monkeypatch.setattr(DUNDER_IMPORT, lack_sem_open)
    parallel = reload_parallel()
    fallback = '_{}_fallback'.format(name.split('_')[0])
    assert getattr(parallel, name) is getattr(parallel, fallback)


@mark.parametrize('name', MAPS)
def test_have_sem_open(name, monkeypatch):
    """Test fallback when sem_open is available."""
    monkeypatch.setattr(DUNDER_IMPORT, have_sem_open)
    parallel = reload_parallel()
    impl = ('_{}_py2' if PY2 else '_{}_py3').format(name)
    assert getattr(parallel, name) is getattr(parallel, impl)


@mark.parametrize('name', MAPS)
def test_map(name):
    """Test correctness of result of asynchronous maps."""
    map_async = getattr(reload_parallel(), name)
    assert set(map_async(FUNC, ITERABLE)) == set(map(FUNC, ITERABLE))


@mark.parametrize('name', ('map_multiprocess', 'map_multithread'))
def test_map_order(name):
    """Test result ordering of asynchronous maps."""
    map_async = getattr(reload_parallel(), name)
    assert tuple(map_async(FUNC, ITERABLE)) == tuple(map(FUNC, ITERABLE))
