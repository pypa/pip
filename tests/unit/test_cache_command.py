"""Tests for the cache command with HTTP cache listing functionality."""

import os
import tempfile
from optparse import Values

from pip._vendor.cachecontrol.serialize import Serializer

from pip._internal.commands.cache import CacheCommand


class TestGetHttpCacheFilesWithMetadata:
    """Tests for _get_http_cache_files_with_metadata method."""

    def test_extracts_filename_from_wheel_body(self) -> None:
        """Test that filenames are extracted from wheel file bodies."""
        import zipfile

        with tempfile.TemporaryDirectory() as cache_dir:
            cache_subdir = os.path.join(cache_dir, "http-v2", "a", "b", "c", "d", "e")
            os.makedirs(cache_subdir, exist_ok=True)

            cache_file = os.path.join(cache_subdir, "test_cache_file")

            # Create a minimal wheel file structure
            body_file = cache_file + ".body"
            with zipfile.ZipFile(body_file, "w") as zf:
                # Wheels have a .dist-info directory
                zf.writestr("test_package-1.0.0.dist-info/WHEEL", "Wheel-Version: 1.0")
                zf.writestr(
                    "test_package-1.0.0.dist-info/METADATA", "Name: test-package"
                )

            # Create cache metadata
            cache_data = {
                "response": {
                    "body": b"",
                    "headers": {
                        "content-type": "application/octet-stream",
                    },
                    "status": 200,
                    "version": 11,
                    "reason": "OK",
                    "decode_content": False,
                },
                "vary": {},
            }

            s = Serializer()
            serialized = s.serialize(cache_data)
            full_data = f"cc={s.serde_version},".encode() + serialized

            with open(cache_file, "wb") as f:
                f.write(full_data)

            options = Values()
            options.cache_dir = cache_dir

            cmd = CacheCommand("cache", "Test cache command")
            result = cmd._get_http_cache_files_with_metadata(options)

            # Should extract filename from wheel structure
            assert len(result) == 1
            assert result[0][0] == cache_file
            assert result[0][1] == "test_package-1.0.0.whl"

    def test_extracts_filename_from_tarball_body(self) -> None:
        """Test that filenames are extracted from tarball file bodies."""
        import tarfile

        with tempfile.TemporaryDirectory() as cache_dir:
            cache_subdir = os.path.join(cache_dir, "http-v2", "a", "b", "c", "d", "e")
            os.makedirs(cache_subdir, exist_ok=True)

            cache_file = os.path.join(cache_subdir, "test_cache_file")

            # Create a minimal tarball structure
            body_file = cache_file + ".body"
            with tarfile.open(body_file, "w:gz") as tf:
                # Tarballs typically have package-version/ as root
                import io

                data = b"test content"
                tarinfo = tarfile.TarInfo(name="mypackage-2.0.0/setup.py")
                tarinfo.size = len(data)
                tf.addfile(tarinfo, io.BytesIO(data))

            # Create cache metadata
            cache_data = {
                "response": {
                    "body": b"",
                    "headers": {
                        "content-type": "application/octet-stream",
                    },
                    "status": 200,
                    "version": 11,
                    "reason": "OK",
                    "decode_content": False,
                },
                "vary": {},
            }

            s = Serializer()
            serialized = s.serialize(cache_data)
            full_data = f"cc={s.serde_version},".encode() + serialized

            with open(cache_file, "wb") as f:
                f.write(full_data)

            options = Values()
            options.cache_dir = cache_dir

            cmd = CacheCommand("cache", "Test cache command")
            result = cmd._get_http_cache_files_with_metadata(options)

            # Should extract filename from tarball structure
            assert len(result) == 1
            assert result[0][0] == cache_file
            assert result[0][1] == "mypackage-2.0.0.tar.gz"

    def test_handles_files_without_extractable_names(self) -> None:
        """Test that files without extractable package names are excluded."""
        with tempfile.TemporaryDirectory() as cache_dir:
            # Create nested directory structure
            cache_subdir = os.path.join(cache_dir, "http-v2", "a", "b", "c", "d", "e")
            os.makedirs(cache_subdir, exist_ok=True)

            # Create a cache file for non-package content (HTML)
            cache_file = os.path.join(cache_subdir, "test_cache_file")

            cache_data = {
                "response": {
                    "body": b"",
                    "headers": {
                        "content-type": "text/html",
                    },
                    "status": 200,
                    "version": 11,
                    "reason": "OK",
                    "decode_content": False,
                },
                "vary": {},
            }

            s = Serializer()
            serialized = s.serialize(cache_data)
            full_data = f"cc={s.serde_version},".encode() + serialized

            with open(cache_file, "wb") as f:
                f.write(full_data)

            # Create mock options
            options = Values()
            options.cache_dir = cache_dir

            # Test the method
            cmd = CacheCommand("cache", "Test cache command")
            result = cmd._get_http_cache_files_with_metadata(options)

            # Should not include files without extractable names
            assert len(result) == 0

    def test_skips_body_files(self) -> None:
        """Test that .body files are skipped."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache_subdir = os.path.join(cache_dir, "http-v2", "a", "b", "c", "d", "e")
            os.makedirs(cache_subdir, exist_ok=True)

            # Create a .body file
            body_file = os.path.join(cache_subdir, "test_cache_file.body")
            with open(body_file, "wb") as f:
                f.write(b"test data")

            options = Values()
            options.cache_dir = cache_dir

            cmd = CacheCommand("cache", "Test cache command")
            result = cmd._get_http_cache_files_with_metadata(options)

            # Should not find any files (body files are skipped)
            assert len(result) == 0

    def test_handles_corrupted_cache_files(self) -> None:
        """Test that corrupted cache files are handled gracefully."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache_subdir = os.path.join(cache_dir, "http-v2", "a", "b", "c", "d", "e")
            os.makedirs(cache_subdir, exist_ok=True)

            # Create a corrupted cache file
            cache_file = os.path.join(cache_subdir, "corrupted_file")
            with open(cache_file, "wb") as f:
                f.write(b"not a valid cache file")

            options = Values()
            options.cache_dir = cache_dir

            cmd = CacheCommand("cache", "Test cache command")
            result = cmd._get_http_cache_files_with_metadata(options)

            # Should handle the corrupted file without crashing
            # Corrupted files without extractable names are excluded
            assert len(result) == 0
