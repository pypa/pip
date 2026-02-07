import os
import sys
from pathlib import Path

import pytest

from pip._internal.utils.compat import get_path_uid, stdlib_module_names


def test_get_path_uid() -> None:
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
def test_get_path_uid_without_NOFOLLOW(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr("os.O_NOFOLLOW")
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


# Skip unconditionally on Windows, as symlinks need admin privs there
@pytest.mark.skipif("sys.platform == 'win32'")
@pytest.mark.skipif("not hasattr(os, 'symlink')")
def test_get_path_uid_symlink(tmpdir: Path) -> None:
    f = tmpdir / "symlink" / "somefile"
    f.parent.mkdir()
    f.write_text("content")
    fs = f"{f}_link"
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
@pytest.mark.skipif("not hasattr(os, 'symlink')")
def test_get_path_uid_symlink_without_NOFOLLOW(
    tmpdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr("os.O_NOFOLLOW")
    f = tmpdir / "symlink" / "somefile"
    f.parent.mkdir()
    f.write_text("content")
    fs = f"{f}_link"
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


def test_stdlib_module_names_type() -> None:
    """Test that stdlib_module_names is a frozenset."""
    assert isinstance(stdlib_module_names, frozenset)


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="sys.stdlib_module_names only available in Python 3.10+",
)
def test_stdlib_module_names_contains_common_modules() -> None:
    """Test that stdlib_module_names contains expected stdlib modules."""
    # These are common stdlib modules that should always be present
    assert "os" in stdlib_module_names
    assert "sys" in stdlib_module_names
    assert "json" in stdlib_module_names
    assert "collections" in stdlib_module_names


@pytest.mark.skipif(
    sys.version_info >= (3, 10),
    reason="Testing fallback behavior on Python < 3.10",
)
def test_stdlib_module_names_empty_on_older_python() -> None:
    """Test that stdlib_module_names is empty on Python < 3.10."""
    assert len(stdlib_module_names) == 0
