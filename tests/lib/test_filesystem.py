import os
import shutil

import psutil
import pytest

from tests.lib.filesystem import FileOpener

skip_unless_windows = pytest.mark.skipif("sys.platform != 'win32'")


@pytest.fixture()
def process():
    return psutil.Process()


def test_file_opener_no_file(process):
    # FileOpener joins the subprocess even if the parent never sends the path
    with FileOpener():
        assert len(process.children()) == 1
    assert len(process.children()) == 0


def test_file_opener_not_found(tmpdir, process):
    # The FileOpener cleans up the subprocess when the file cannot be opened
    path = tmpdir.joinpath('foo.txt')
    with FileOpener(path):
        assert len(process.children()) == 1
    assert len(process.children()) == 0


def test_file_opener_normal(tmpdir, process):
    # The FileOpener cleans up the subprocess when the file exists
    path = tmpdir.joinpath('foo.txt')
    path.write_text('Hello')
    with FileOpener(path):
        assert len(process.children()) == 1
    assert len(process.children()) == 0


@skip_unless_windows
def test_file_opener_produces_unlink_error(tmpdir, process):
    # FileOpener forces an error on Windows when we attempt to remove a file
    # The initial path may be deferred; which must be tested with an error
    path = tmpdir.joinpath('foo.txt')
    path.write_text('Hello')
    with FileOpener() as opener:
        opener.send(path)
        with pytest.raises(OSError):
            os.unlink(path)


@skip_unless_windows
def test_file_opener_produces_rmtree_error(tmpdir, process):
    subdir = tmpdir.joinpath('foo')
    os.mkdir(subdir)
    path = subdir.joinpath('bar.txt')
    path.write_text('Hello')
    with FileOpener(path):
        with pytest.raises(OSError):
            shutil.rmtree(subdir)
