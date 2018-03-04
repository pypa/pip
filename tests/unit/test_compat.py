import locale
import os

import pytest

import pip._internal.compat
from pip._internal.compat import (
    console_to_str, expanduser, get_path_uid, native_str,
)


def test_get_path_uid():
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
def test_get_path_uid_without_NOFOLLOW(monkeypatch):
    monkeypatch.delattr("os.O_NOFOLLOW")
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


# Skip unconditionally on Windows, as symlinks need admin privs there
@pytest.mark.skipif("sys.platform == 'win32'")
@pytest.mark.skipif("not hasattr(os, 'symlink')")
def test_get_path_uid_symlink(tmpdir):
    f = tmpdir.mkdir("symlink").join("somefile")
    f.write("content")
    fs = f + '_link'
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
@pytest.mark.skipif("not hasattr(os, 'symlink')")
def test_get_path_uid_symlink_without_NOFOLLOW(tmpdir, monkeypatch):
    monkeypatch.delattr("os.O_NOFOLLOW")
    f = tmpdir.mkdir("symlink").join("somefile")
    f.write("content")
    fs = f + '_link'
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


def test_console_to_str(monkeypatch):
    some_bytes = b"a\xE9\xC3\xE9b"
    encodings = ('ascii', 'utf-8', 'iso-8859-1', 'iso-8859-5',
                 'koi8_r', 'cp850')
    for e in encodings:
        monkeypatch.setattr(locale, 'getpreferredencoding', lambda: e)
        result = console_to_str(some_bytes)
        assert result.startswith("a")
        assert result.endswith("b")


def test_console_to_str_warning(monkeypatch):
    some_bytes = b"a\xE9b"

    def check_warning(msg, *args, **kwargs):
        assert msg.startswith(
            "Subprocess output does not appear to be encoded as")

    monkeypatch.setattr(locale, 'getpreferredencoding', lambda: 'utf-8')
    monkeypatch.setattr(pip._internal.compat.logger, 'warning', check_warning)
    console_to_str(some_bytes)


def test_to_native_str_type():
    some_bytes = b"test\xE9 et approuv\xC3\xE9"
    some_unicode = b"test\xE9 et approuv\xE9".decode('iso-8859-15')
    assert isinstance(native_str(some_bytes, True), str)
    assert isinstance(native_str(some_unicode, True), str)


@pytest.mark.parametrize("home,path,expanded", [
    ("/Users/test", "~", "/Users/test"),
    ("/Users/test", "~/.cache", "/Users/test/.cache"),
    # Verify that we are not affected by http://bugs.python.org/issue14768
    ("/", "~", "/"),
    ("/", "~/.cache", "/.cache"),
])
def test_expanduser(home, path, expanded, monkeypatch):
    monkeypatch.setenv("HOME", home)
    assert expanduser(path) == expanded
