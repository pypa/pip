# -*- coding: utf-8 -*-

import locale
import os
import sys

import pytest

import pip._internal.utils.compat as pip_compat
from pip._internal.utils.compat import (
    console_to_str,
    expanduser,
    get_path_uid,
    str_to_display,
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
    f = tmpdir / "symlink" / "somefile"
    f.parent.mkdir()
    f.write_text("content")
    fs = f + '_link'
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
@pytest.mark.skipif("not hasattr(os, 'symlink')")
def test_get_path_uid_symlink_without_NOFOLLOW(tmpdir, monkeypatch):
    monkeypatch.delattr("os.O_NOFOLLOW")
    f = tmpdir / "symlink" / "somefile"
    f.parent.mkdir()
    f.write_text("content")
    fs = f + '_link'
    os.symlink(f, fs)
    with pytest.raises(OSError):
        get_path_uid(fs)


@pytest.mark.parametrize('data, expected', [
    ('abc', u'abc'),
    # Test text (unicode in Python 2) input.
    (u'abc', u'abc'),
    # Test text input with non-ascii characters.
    (u'déf', u'déf'),
])
def test_str_to_display(data, expected):
    actual = str_to_display(data)
    assert actual == expected, (
        # Show the encoding for easier troubleshooting.
        'encoding: {!r}'.format(locale.getpreferredencoding())
    )


@pytest.mark.parametrize('data, encoding, expected', [
    # Test str input with non-ascii characters.
    ('déf', 'utf-8', u'déf'),
    # Test bytes input with non-ascii characters:
    (u'déf'.encode('utf-8'), 'utf-8', u'déf'),
    # Test a Windows encoding.
    (u'déf'.encode('cp1252'), 'cp1252', u'déf'),
    # Test a Windows encoding with incompatibly encoded text.
    (u'déf'.encode('utf-8'), 'cp1252', u'dÃ©f'),
])
def test_str_to_display__encoding(monkeypatch, data, encoding, expected):
    monkeypatch.setattr(locale, 'getpreferredencoding', lambda: encoding)
    actual = str_to_display(data)
    assert actual == expected, (
        # Show the encoding for easier troubleshooting.
        'encoding: {!r}'.format(locale.getpreferredencoding())
    )


def test_str_to_display__decode_error(monkeypatch, caplog):
    monkeypatch.setattr(locale, 'getpreferredencoding', lambda: 'utf-8')
    # Encode with an incompatible encoding.
    data = u'ab'.encode('utf-16')
    actual = str_to_display(data)
    # Keep the expected value endian safe
    if sys.byteorder == "little":
        expected = "\\xff\\xfea\x00b\x00"
    elif sys.byteorder == "big":
        expected = "\\xfe\\xff\x00a\x00b"

    assert actual == expected, (
        # Show the encoding for easier troubleshooting.
        'encoding: {!r}'.format(locale.getpreferredencoding())
    )
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'WARNING'
    assert record.message == (
        'Bytes object does not appear to be encoded as utf-8'
    )


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
        assert 'does not appear to be encoded as' in msg
        assert args[0] == 'Subprocess output'

    monkeypatch.setattr(locale, 'getpreferredencoding', lambda: 'utf-8')
    monkeypatch.setattr(pip_compat.logger, 'warning', check_warning)
    console_to_str(some_bytes)


@pytest.mark.parametrize("home,path,expanded", [
    ("/Users/test", "~", "/Users/test"),
    ("/Users/test", "~/.cache", "/Users/test/.cache"),
    # Verify that we are not affected by https://bugs.python.org/issue14768
    ("/", "~", "/"),
    ("/", "~/.cache", "/.cache"),
])
def test_expanduser(home, path, expanded, monkeypatch):
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("USERPROFILE", home)
    assert expanduser(path) == expanded
