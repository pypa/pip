import os
from pip.compat import get_path_uid
import pytest


def test_get_path_uid():
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


@pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
def test_get_path_uid_without_NOFOLLOW(monkeypatch):
    monkeypatch.delattr("os.O_NOFOLLOW")
    path = os.getcwd()
    assert get_path_uid(path) == os.stat(path).st_uid


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
