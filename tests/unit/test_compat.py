import locale
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pip._internal.utils.compat import get_locale_encoding, get_path_uid


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


def test_get_locale_encoding_utf8_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """The locale encoding is UTF-8 when UTF-8 Mode is enabled."""
    monkeypatch.setattr(sys, "flags", SimpleNamespace(utf8_mode=True))
    assert get_locale_encoding() == "utf-8"


def test_get_locale_encoding_without_utf8_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The locale encoding is used when UTF-8 Mode is disabled."""
    monkeypatch.setattr(sys, "flags", SimpleNamespace(utf8_mode=False))
    if sys.version_info >= (3, 11):
        monkeypatch.setattr(locale, "getencoding", lambda: "cp936")
    else:
        monkeypatch.setattr(
            locale, "getpreferredencoding", lambda do_setlocale=True: "cp936"
        )
    assert get_locale_encoding() == "cp936"
