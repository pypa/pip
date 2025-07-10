import os
import sys
import urllib.request

import pytest

from pip._internal.utils.urls import path_to_url, url_to_path


@pytest.mark.skipif("sys.platform == 'win32'")
def test_path_to_url_unix() -> None:
    assert path_to_url("/tmp/file") == "file:///tmp/file"
    path = os.path.join(os.getcwd(), "file")
    assert path_to_url("file") == "file://" + urllib.request.pathname2url(path)


@pytest.mark.skipif("sys.platform != 'win32'")
@pytest.mark.parametrize(
    "path, url",
    [
        pytest.param("c:/tmp/file", "file:///C:/tmp/file", id="posix-path"),
        pytest.param("c:\\tmp\\file", "file:///C:/tmp/file", id="nt-path"),
    ],
)
def test_path_to_url_win(path: str, url: str) -> None:
    assert path_to_url(path) == url


@pytest.mark.skipif("sys.platform != 'win32'")
def test_unc_path_to_url_win() -> None:
    # The two and four slash forms are both acceptable for our purposes. CPython's
    # behaviour has changed several times here, so blindly accept either.
    # - https://github.com/python/cpython/issues/78457
    # - https://github.com/python/cpython/issues/126205
    url = path_to_url(r"\\unc\as\path")
    assert url in ["file://unc/as/path", "file:////unc/as/path"]


@pytest.mark.skipif("sys.platform != 'win32'")
def test_relative_path_to_url_win() -> None:
    resolved_path = os.path.join(os.getcwd(), "file")
    assert path_to_url("file") == "file:" + urllib.request.pathname2url(resolved_path)


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
