from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pip._vendor.packaging.pylock import (
    PackageArchive,
    PackageDirectory,
    PackageSdist,
    PackageVcs,
    PackageWheel,
)

from pip._internal.exceptions import InstallationError
from pip._internal.utils.pylock import (
    _package_dist_url,
    package_archive_requirement_url,
    package_directory_requirement_url,
    package_sdist_requirement_url,
    package_vcs_requirement_url,
    package_wheel_requirement_url,
)
from pip._internal.utils.urls import path_to_url


def _adapt_full_path_url(url: str) -> str:
    """A little hack to adapt absolute file:/// url to windows drive letter."""
    if sys.platform == "win32" and url.startswith("file:///"):
        return url.replace("file:///", path_to_url("/a")[:-1])
    return url


@pytest.mark.parametrize(
    "pylock_filename_or_url,path,url,expected",
    [
        (
            # URL, no path
            "pylock.toml",
            None,
            "https://example.com/foo.tar.gz",
            "https://example.com/foo.tar.gz",
        ),
        (
            # path over URL, joined with pylock.toml dir
            "/base/pylock.toml",
            "foo.tar.gz",
            "https://example.com/foo.tar.gz",
            "file:///base/foo.tar.gz",
        ),
        (
            # absolute path over URL, not joined with pylock.toml dir
            "/base/pylock.toml",
            "/there/foo.tar.gz",
            "https://example.com/foo.tar.gz",
            "file:///there/foo.tar.gz",
        ),
        (
            # relative path joined with pylock.toml http url
            "https://example.com/pylock.toml",
            "./there/foo.tar.gz",
            None,
            "https://example.com/there/foo.tar.gz",
        ),
    ],
)
def test_package_dist_url(
    pylock_filename_or_url: str,
    path: str | None,
    url: str | None,
    expected: str,
) -> None:
    assert _package_dist_url(pylock_filename_or_url, path, url) == _adapt_full_path_url(
        expected
    )


def test_package_dist_url_abs_path_remote_lock_file() -> None:
    """A remote lock file cannot have package with absolute paths."""
    with pytest.raises(InstallationError, match="Absolute path are not supported"):
        _package_dist_url(
            "https://example.com/pylock.toml",
            path=str(Path("/here/pkg.tgz").absolute()),
            url=None,
        )


@pytest.mark.parametrize(
    "pylock_path_or_url,package_vcs,expected",
    [
        (
            "pylock.toml",
            PackageVcs(
                type="git",
                url="https://g.c/o/p.git",
                commit_id="ccc",
            ),
            "git+https://g.c/o/p.git@ccc",
        ),
        (
            "pylock.toml",
            PackageVcs(
                type="git",
                url="https://g.c/o/p.git",
                commit_id="ccc",
                subdirectory="setup",
            ),
            "git+https://g.c/o/p.git@ccc#subdirectory=setup",
        ),
    ],
)
def test_package_vcs_requirement_url(
    pylock_path_or_url: str, package_vcs: PackageVcs, expected: str
) -> None:
    assert package_vcs_requirement_url(
        pylock_path_or_url, package_vcs
    ) == _adapt_full_path_url(expected)


@pytest.mark.parametrize(
    "pylock_path_or_url,package_archive,expected",
    [
        (
            "pylock.toml",
            PackageArchive(
                url="https://example.com/archive.tgz",
                hashes={"sha256": "aaa"},
            ),
            "https://example.com/archive.tgz",
        ),
        (
            "pylock.toml",
            PackageArchive(
                url="https://example.com/archive.tgz",
                subdirectory="subdir",
                hashes={"sha256": "aaa"},
            ),
            "https://example.com/archive.tgz#subdirectory=subdir",
        ),
        (
            "https://example.com/pylock.toml",
            PackageArchive(
                path="archive.tgz",
                hashes={"sha256": "aaa"},
            ),
            "https://example.com/archive.tgz",
        ),
        (
            "/path/to/pylock.toml",
            PackageArchive(
                path="archive.tgz",
                hashes={"sha256": "aaa"},
            ),
            "file:///path/to/archive.tgz",
        ),
    ],
)
def test_package_archive_requirement_url(
    pylock_path_or_url: str, package_archive: PackageArchive, expected: str
) -> None:
    assert package_archive_requirement_url(
        pylock_path_or_url, package_archive
    ) == _adapt_full_path_url(expected)


@pytest.mark.parametrize(
    "pylock_path_or_url,package_directory,expected",
    [
        (
            "/path/to/pylock.toml",
            PackageDirectory(path="dir"),
            "file:///path/to/dir/",
        ),
        (
            "/path/to/pylock.toml",
            PackageDirectory(path="dir", subdirectory="subdir"),
            "file:///path/to/dir/subdir/",
        ),
    ],
)
def test_package_directory_requirement_url(
    pylock_path_or_url: str, package_directory: PackageDirectory, expected: str
) -> None:
    assert package_directory_requirement_url(
        pylock_path_or_url, package_directory
    ) == _adapt_full_path_url(expected)


@pytest.mark.parametrize(
    "pylock_path_or_url,package_sdist,expected",
    [
        (
            "https://example.com/pylock.toml",
            PackageSdist(
                path="pkga-1.0.tar.gz",
                hashes={"sha256": "aaa"},
            ),
            "https://example.com/pkga-1.0.tar.gz",
        ),
    ],
)
def test_package_sdist_requirement_url(
    pylock_path_or_url: str, package_sdist: PackageSdist, expected: str
) -> None:
    assert package_sdist_requirement_url(
        pylock_path_or_url, package_sdist
    ) == _adapt_full_path_url(expected)


@pytest.mark.parametrize(
    "pylock_path_or_url,package_wheel,expected",
    [
        (
            "pylock.toml",
            PackageWheel(
                url="https://there.org/wheel_1.0_py3-none-any.whl",
                hashes={"sha256": "aaa"},
            ),
            "https://there.org/wheel_1.0_py3-none-any.whl",
        ),
    ],
)
def test_package_wheel_requirement_url(
    pylock_path_or_url: str, package_wheel: PackageWheel, expected: str
) -> None:
    assert package_wheel_requirement_url(
        pylock_path_or_url, package_wheel
    ) == _adapt_full_path_url(expected)
