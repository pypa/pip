import os
import sys
import urllib.request
from typing import Optional

import pytest

from pip._internal.utils.urls import get_url_scheme, path_to_url, url_to_path


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://localhost:8080/", "http"),
        ("file:c:/path/to/file", "file"),
        ("file:/dev/null", "file"),
        ("", None),
    ],
)
def test_get_url_scheme(url: str, expected: Optional[str]) -> None:
    assert get_url_scheme(url) == expected


@pytest.mark.skipif("sys.platform == 'win32'")
def test_path_to_url_unix() -> None:
    assert path_to_url("/tmp/file") == "file:///tmp/file"
    path = os.path.join(os.getcwd(), "file")
    assert path_to_url("file") == "file://" + urllib.request.pathname2url(path)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_path_to_url_win() -> None:
    assert path_to_url("c:/tmp/file") == "file:///C:/tmp/file"
    assert path_to_url("c:\\tmp\\file") == "file:///C:/tmp/file"
    assert path_to_url(r"\\unc\as\path") == "file://unc/as/path"
    path = os.path.join(os.getcwd(), "file")
    assert path_to_url("file") == "file:" + urllib.request.pathname2url(path)


@pytest.mark.parametrize(
    "url,win_expected,non_win_expected",
    [
        ("file:tmp", "tmp", "tmp"),
        ("file:c:/path/to/file", r"C:\path\to\file", "c:/path/to/file"),
        ("file:/path/to/file", r"\path\to\file", "/path/to/file"),
        ("file://localhost/tmp/file", r"\tmp\file", "/tmp/file"),
        ("file://localhost/c:/tmp/file", r"C:\tmp\file", "/c:/tmp/file"),
        ("file://somehost/tmp/file", r"\\somehost\tmp\file", None),
        ("file:///tmp/file", r"\tmp\file", "/tmp/file"),
        ("file:///c:/tmp/file", r"C:\tmp\file", "/c:/tmp/file"),
    ],
)
def test_url_to_path(url: str, win_expected: str, non_win_expected: str) -> None:
    if sys.platform == "win32":
        expected_path = win_expected
    else:
        expected_path = non_win_expected

    if expected_path is None:
        with pytest.raises(ValueError):
            url_to_path(url)
    else:
        assert url_to_path(url) == expected_path


@pytest.mark.skipif("sys.platform != 'win32'")
def test_url_to_path_path_to_url_symmetry_win() -> None:
    path = r"C:\tmp\file"
    assert url_to_path(path_to_url(path)) == path

    unc_path = r"\\unc\share\path"
    assert url_to_path(path_to_url(unc_path)) == unc_path
