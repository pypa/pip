"""Test multiprocessing/multithreading higher-order functions."""

from contextlib import contextmanager
from importlib import import_module
from math import factorial
from sys import modules

from pytest import mark

DUNDER_IMPORT = "builtins.__import__"
FUNC, ITERABLE = factorial, range(42)
MAPS = "map_multiprocess", "map_multithread"
_import = __import__


def unload_parallel():
    try:
        del modules["pip._internal.utils.parallel"]
    except KeyError:
        pass


@contextmanager
def tmp_import_parallel():
    unload_parallel()
    try:
        yield import_module("pip._internal.utils.parallel")
    finally:
        unload_parallel()


def lack_sem_open(name, *args, **kwargs):
    """Raise ImportError on import of multiprocessing.synchronize."""
    if name.endswith("synchronize"):
        raise ImportError
    return _import(name, *args, **kwargs)


def have_sem_open(name, *args, **kwargs):
    """Make sure multiprocessing.synchronize import is successful."""
    # We don't care about the return value
    # since we don't use the pool with this import.
    if name.endswith("synchronize"):
        return
    return _import(name, *args, **kwargs)


@mark.parametrize("name", MAPS)
def test_lack_sem_open(name, monkeypatch):
    """Test fallback when sem_open is not available.

    If so, multiprocessing[.dummy].Pool will fail to be created and
    map_async should fallback to map.
    """
    monkeypatch.setattr(DUNDER_IMPORT, lack_sem_open)
    with tmp_import_parallel() as parallel:
        assert getattr(parallel, name) is parallel._map_fallback


@mark.parametrize("name", MAPS)
def test_have_sem_open(name, monkeypatch):
    """Test fallback when sem_open is available."""
    monkeypatch.setattr(DUNDER_IMPORT, have_sem_open)
    with tmp_import_parallel() as parallel:
        assert getattr(parallel, name) is getattr(parallel, f"_{name}")


@mark.parametrize("name", MAPS)
def test_map(name):
    """Test correctness of result of asynchronous maps."""
    map_async = getattr(import_module("pip._internal.utils.parallel"), name)
    assert set(map_async(FUNC, ITERABLE)) == set(map(FUNC, ITERABLE))
