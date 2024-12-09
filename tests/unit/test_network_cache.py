import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from pip._vendor.cachecontrol.caches import FileCache

from pip._internal.network.cache import SafeFileCache

from tests.lib.filesystem import chmod


@pytest.fixture
def cache_tmpdir(tmpdir: Path) -> Path:
    cache_dir = tmpdir.joinpath("cache")
    cache_dir.mkdir(parents=True)
    return cache_dir


class TestSafeFileCache:
    """
    The no_perms test are useless on Windows since SafeFileCache uses
    pip._internal.utils.filesystem.check_path_owner which is based on
    os.geteuid which is absent on Windows.
    """

    def test_cache_roundtrip(self, cache_tmpdir: Path) -> None:
        cache = SafeFileCache(os.fspath(cache_tmpdir))
        assert cache.get("test key") is None
        cache.set("test key", b"a test string")
        # Body hasn't been stored yet, so the entry isn't valid yet
        assert cache.get("test key") is None

        # With a body, the cache entry is valid:
        cache.set_body("test key", b"body")
        assert cache.get("test key") == b"a test string"
        cache.delete("test key")
        assert cache.get("test key") is None

    def test_cache_roundtrip_body(self, cache_tmpdir: Path) -> None:
        cache = SafeFileCache(os.fspath(cache_tmpdir))
        assert cache.get_body("test key") is None
        cache.set_body("test key", b"a test string")
        # Metadata isn't available, so the entry isn't valid yet (this
        # shouldn't happen, but just in case)
        assert cache.get_body("test key") is None

        # With metadata, the cache entry is valid:
        cache.set("test key", b"metadata")
        body = cache.get_body("test key")
        assert body is not None
        with body:
            assert body.read() == b"a test string"
        cache.delete("test key")
        assert cache.get_body("test key") is None

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_get_no_perms(
        self, cache_tmpdir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os.path, "exists", lambda x: True)

        with chmod(cache_tmpdir, 000):
            cache = SafeFileCache(os.fspath(cache_tmpdir))
            cache.get("foo")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_set_no_perms(self, cache_tmpdir: Path) -> None:
        with chmod(cache_tmpdir, 000):
            cache = SafeFileCache(os.fspath(cache_tmpdir))
            cache.set("foo", b"bar")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_delete_no_perms(self, cache_tmpdir: Path) -> None:
        with chmod(cache_tmpdir, 000):
            cache = SafeFileCache(os.fspath(cache_tmpdir))
            cache.delete("foo")

    def test_cache_hashes_are_same(self, cache_tmpdir: Path) -> None:
        cache = SafeFileCache(os.fspath(cache_tmpdir))
        key = "test key"
        fake_cache = Mock(FileCache, directory=cache.directory, encode=FileCache.encode)
        assert cache._get_cache_path(key) == FileCache._fn(fake_cache, key)

    @pytest.mark.skipif("sys.platform == 'win32'")
    @pytest.mark.skipif(
        os.chmod not in os.supports_fd and os.chmod not in os.supports_follow_symlinks,
        reason="requires os.chmod to support file descriptors or not follow symlinks",
    )
    @pytest.mark.parametrize(
        "perms, expected_perms", [(0o300, 0o600), (0o700, 0o600), (0o777, 0o666)]
    )
    def test_cache_inherit_perms(
        self, cache_tmpdir: Path, perms: int, expected_perms: int
    ) -> None:
        key = "foo"
        with chmod(cache_tmpdir, perms):
            cache = SafeFileCache(os.fspath(cache_tmpdir))
            cache.set(key, b"bar")
        assert (os.stat(cache._get_cache_path(key)).st_mode & 0o777) == expected_perms

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_cache_not_inherit_perms(
        self, cache_tmpdir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "supports_fd", os.supports_fd - {os.chmod})
        monkeypatch.setattr(
            os, "supports_follow_symlinks", os.supports_follow_symlinks - {os.chmod}
        )
        key = "foo"
        with chmod(cache_tmpdir, 0o777):
            cache = SafeFileCache(os.fspath(cache_tmpdir))
            cache.set(key, b"bar")
        assert (os.stat(cache._get_cache_path(key)).st_mode & 0o777) == 0o600
