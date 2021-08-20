import os
from unittest.mock import Mock

import pytest
from pip._vendor.cachecontrol.caches import FileCache

from pip._internal.network.cache import SafeFileCache


@pytest.fixture(scope="function")
def cache_tmpdir(tmpdir):
    cache_dir = tmpdir.joinpath("cache")
    cache_dir.mkdir(parents=True)
    yield cache_dir


class TestSafeFileCache:
    """
    The no_perms test are useless on Windows since SafeFileCache uses
    pip._internal.utils.filesystem.check_path_owner which is based on
    os.geteuid which is absent on Windows.
    """

    def test_cache_roundtrip(self, cache_tmpdir):

        cache = SafeFileCache(cache_tmpdir)
        assert cache.get("test key") is None
        cache.set("test key", b"a test string")
        assert cache.get("test key") == b"a test string"
        cache.delete("test key")
        assert cache.get("test key") is None

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_get_no_perms(self, cache_tmpdir, monkeypatch):
        os.chmod(cache_tmpdir, 000)

        monkeypatch.setattr(os.path, "exists", lambda x: True)

        cache = SafeFileCache(cache_tmpdir)
        cache.get("foo")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_set_no_perms(self, cache_tmpdir):
        os.chmod(cache_tmpdir, 000)

        cache = SafeFileCache(cache_tmpdir)
        cache.set("foo", b"bar")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_delete_no_perms(self, cache_tmpdir):
        os.chmod(cache_tmpdir, 000)

        cache = SafeFileCache(cache_tmpdir)
        cache.delete("foo")

    def test_cache_hashes_are_same(self, cache_tmpdir):
        cache = SafeFileCache(cache_tmpdir)
        key = "test key"
        fake_cache = Mock(FileCache, directory=cache.directory, encode=FileCache.encode)
        assert cache._get_cache_path(key) == FileCache._fn(fake_cache, key)
