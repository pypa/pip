"""Test multiprocessing/multithreading higher-order functions."""

from math import factorial

from mock import patch
from pip._vendor.six import PY2
from pip._vendor.six.moves import map
from pytest import mark

from pip._internal.utils.parallel import map_multiprocess, map_multithread

DUNDER_IMPORT = '__builtin__.__import__' if PY2 else 'builtins.__import__'
FUNC, ITERABLE = factorial, range(42)


def import_sem_open(name, *args, **kwargs):
    """Raise ImportError on import of multiprocessing.synchronize."""
    if name.endswith('.synchronize'):
        raise ImportError


@mark.parametrize('map_async', (map_multiprocess, map_multithread))
def test_missing_sem_open(map_async, monkeypatch):
    """Test fallback when sem_open is not available.

    If so, multiprocessing[.dummy].Pool will fail to be created and
    map_async should fallback to map and still return correct result.
    """
    with patch(DUNDER_IMPORT, side_effect=import_sem_open):
        assert map_async(FUNC, ITERABLE) == list(map(FUNC, ITERABLE))


@mark.parametrize('map_async', (map_multiprocess, map_multithread))
def test_map_order(map_async):
    """Test result ordering of asynchronous maps."""
    assert map_async(FUNC, ITERABLE) == list(map(FUNC, ITERABLE))
