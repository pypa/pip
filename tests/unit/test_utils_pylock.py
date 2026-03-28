from __future__ import annotations

import pytest

from pip._internal.utils.pylock import _package_dist_url
from pip._internal.utils.urls import path_to_url


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
    if expected.startswith("file:///"):
        expected = expected.replace("file:///", path_to_url("/"))
    assert _package_dist_url(pylock_filename_or_url, path, url) == expected
