import os
import sys
import urllib.request

import pytest

from pip._internal.utils.urls import (
    _clean_url_path,
    clean_url,
    path_to_url,
    url_to_path,
)

from tests.lib import (
    skip_needs_new_pathname2url_trailing_slash_behavior_win,
    skip_needs_new_urlun_behavior_win,
    skip_needs_old_pathname2url_trailing_slash_behavior_win,
    skip_needs_old_urlun_behavior_win,
)


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


@pytest.mark.parametrize(
    "path, expected",
    [
        # Test a character that needs quoting.
        ("a b", "a%20b"),
        # Test an unquoted "@".
        ("a @ b", "a%20@%20b"),
        # Test multiple unquoted "@".
        ("a @ @ b", "a%20@%20@%20b"),
        # Test a quoted "@".
        ("a %40 b", "a%20%40%20b"),
        # Test a quoted "@" before an unquoted "@".
        ("a %40b@ c", "a%20%40b@%20c"),
        # Test a quoted "@" after an unquoted "@".
        ("a @b%40 c", "a%20@b%40%20c"),
        # Test alternating quoted and unquoted "@".
        ("a %40@b %40@c %40", "a%20%40@b%20%40@c%20%40"),
        # Test an unquoted "/".
        ("a / b", "a%20/%20b"),
        # Test multiple unquoted "/".
        ("a / / b", "a%20/%20/%20b"),
        # Test a quoted "/".
        ("a %2F b", "a%20%2F%20b"),
        # Test a quoted "/" before an unquoted "/".
        ("a %2Fb/ c", "a%20%2Fb/%20c"),
        # Test a quoted "/" after an unquoted "/".
        ("a /b%2F c", "a%20/b%2F%20c"),
        # Test alternating quoted and unquoted "/".
        ("a %2F/b %2F/c %2F", "a%20%2F/b%20%2F/c%20%2F"),
        # Test normalizing non-reserved quoted characters "[" and "]"
        ("a %5b %5d b", "a%20%5B%20%5D%20b"),
        # Test normalizing a reserved quoted "/"
        ("a %2f b", "a%20%2F%20b"),
    ],
)
@pytest.mark.parametrize("is_local_path", [True, False])
def test_clean_url_path(path: str, expected: str, is_local_path: bool) -> None:
    assert _clean_url_path(path, is_local_path=is_local_path) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        # Test a VCS path with a Windows drive letter and revision.
        pytest.param(
            "/T:/with space/repo.git@1.0",
            "///T:/with%20space/repo.git@1.0",
            marks=pytest.mark.skipif("sys.platform != 'win32'"),
        ),
        # Test a VCS path with a Windows drive letter and revision,
        # running on non-windows platform.
        pytest.param(
            "/T:/with space/repo.git@1.0",
            "/T%3A/with%20space/repo.git@1.0",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
    ],
)
def test_clean_url_path_with_local_path(path: str, expected: str) -> None:
    actual = _clean_url_path(path, is_local_path=True)
    assert actual == expected


@pytest.mark.parametrize(
    "url, expected_url",
    [
        # URL with hostname and port. Port separator should not be quoted.
        (
            "https://localhost.localdomain:8181/path/with space/",
            "https://localhost.localdomain:8181/path/with%20space/",
        ),
        # URL that is already properly quoted. The quoting `%`
        # characters should not be quoted again.
        (
            "https://localhost.localdomain:8181/path/with%20quoted%20space/",
            "https://localhost.localdomain:8181/path/with%20quoted%20space/",
        ),
        # URL with IPv4 address and port.
        (
            "https://127.0.0.1:8181/path/with space/",
            "https://127.0.0.1:8181/path/with%20space/",
        ),
        # URL with IPv6 address and port. The `[]` brackets around the
        # IPv6 address should not be quoted.
        (
            "https://[fd00:0:0:236::100]:8181/path/with space/",
            "https://[fd00:0:0:236::100]:8181/path/with%20space/",
        ),
        # URL with query. The leading `?` should not be quoted.
        (
            "https://localhost.localdomain:8181/path/with/query?request=test",
            "https://localhost.localdomain:8181/path/with/query?request=test",
        ),
        # URL with colon in the path portion.
        (
            "https://localhost.localdomain:8181/path:/with:/colon",
            "https://localhost.localdomain:8181/path%3A/with%3A/colon",
        ),
        # URL with something that looks like a drive letter, but is
        # not. The `:` should be quoted.
        (
            "https://localhost.localdomain/T:/path/",
            "https://localhost.localdomain/T%3A/path/",
        ),
        # URL with a quoted "/" in the path portion.
        (
            "https://example.com/access%2Ftoken/path/",
            "https://example.com/access%2Ftoken/path/",
        ),
        # VCS URL containing revision string.
        (
            "git+ssh://example.com/path to/repo.git@1.0#egg=my-package-1.0",
            "git+ssh://example.com/path%20to/repo.git@1.0#egg=my-package-1.0",
        ),
        # VCS URL with a quoted "#" in the revision string.
        (
            "git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0",
            "git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0",
        ),
        # VCS URL with a quoted "@" in the revision string.
        (
            "git+https://example.com/repo.git@at%40 space#egg=my-package-1.0",
            "git+https://example.com/repo.git@at%40%20space#egg=my-package-1.0",
        ),
        # URL with Windows drive letter. The `:` after the drive
        # letter should not be quoted. The trailing `/` should be
        # removed.
        pytest.param(
            "file:///T:/path/with spaces/",
            "file:///T:/path/with%20spaces",
            marks=[
                skip_needs_old_urlun_behavior_win,
                skip_needs_old_pathname2url_trailing_slash_behavior_win,
            ],
        ),
        pytest.param(
            "file:///T:/path/with spaces/",
            "file://///T:/path/with%20spaces",
            marks=[
                skip_needs_new_urlun_behavior_win,
                skip_needs_old_pathname2url_trailing_slash_behavior_win,
            ],
        ),
        pytest.param(
            "file:///T:/path/with spaces/",
            "file://///T:/path/with%20spaces/",
            marks=[
                skip_needs_new_urlun_behavior_win,
                skip_needs_new_pathname2url_trailing_slash_behavior_win,
            ],
        ),
        # URL with Windows drive letter, running on non-windows
        # platform. The `:` after the drive should be quoted.
        pytest.param(
            "file:///T:/path/with spaces/",
            "file:///T%3A/path/with%20spaces/",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
        # Test a VCS URL with a Windows drive letter and revision.
        pytest.param(
            "git+file:///T:/with space/repo.git@1.0#egg=my-package-1.0",
            "git+file:///T:/with%20space/repo.git@1.0#egg=my-package-1.0",
            marks=skip_needs_old_urlun_behavior_win,
        ),
        pytest.param(
            "git+file:///T:/with space/repo.git@1.0#egg=my-package-1.0",
            "git+file://///T:/with%20space/repo.git@1.0#egg=my-package-1.0",
            marks=skip_needs_new_urlun_behavior_win,
        ),
        # Test a VCS URL with a Windows drive letter and revision,
        # running on non-windows platform.
        pytest.param(
            "git+file:///T:/with space/repo.git@1.0#egg=my-package-1.0",
            "git+file:/T%3A/with%20space/repo.git@1.0#egg=my-package-1.0",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
    ],
)
def test_clean_url(url: str, expected_url: str) -> None:
    assert clean_url(url) == expected_url
