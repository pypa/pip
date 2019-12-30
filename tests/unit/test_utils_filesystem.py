import os
import shutil

import psutil
import pytest

from pip._internal.utils.filesystem import copy2_fixed, is_socket
from tests.lib.filesystem import (
    FileOpener,
    make_socket_file,
    make_unreadable_file,
)
from tests.lib.path import Path


@pytest.fixture()
def process():
    return psutil.Process()


def make_file(path):
    Path(path).touch()


def make_valid_symlink(path):
    target = path + "1"
    make_file(target)
    os.symlink(target, path)


def make_broken_symlink(path):
    os.symlink("foo", path)


def make_dir(path):
    os.mkdir(path)


skip_on_windows = pytest.mark.skipif("sys.platform == 'win32'")
skip_unless_windows = pytest.mark.skipif("sys.platform != 'win32'")


@skip_on_windows
@pytest.mark.parametrize("create,result", [
    (make_socket_file, True),
    (make_file, False),
    (make_valid_symlink, False),
    (make_broken_symlink, False),
    (make_dir, False),
])
def test_is_socket(create, result, tmpdir):
    target = tmpdir.joinpath("target")
    create(target)
    assert os.path.lexists(target)
    assert is_socket(target) == result


@pytest.mark.parametrize("create,error_type", [
    pytest.param(
        make_socket_file, shutil.SpecialFileError, marks=skip_on_windows
    ),
    (make_unreadable_file, OSError),
])
def test_copy2_fixed_raises_appropriate_errors(create, error_type, tmpdir):
    src = tmpdir.joinpath("src")
    create(src)
    dest = tmpdir.joinpath("dest")

    with pytest.raises(error_type):
        copy2_fixed(src, dest)

    assert not dest.exists()


def test_file_opener_no_file(process):
    # FileOpener joins the subprocess even if the parent never sends the path
    with FileOpener():
        pass
    assert len(process.children()) == 0


def test_file_opener_not_found(tmpdir, process):
    # The FileOpener cleans up the subprocess when the file cannot be opened
    path = tmpdir.joinpath('foo.txt')
    with FileOpener(path):
        pass
    assert len(process.children()) == 0


def test_file_opener_normal(tmpdir, process):
    # The FileOpener cleans up the subprocess when the file exists
    path = tmpdir.joinpath('foo.txt')
    with open(path, 'w') as f:
        f.write('Hello\n')
    with FileOpener(path):
        pass
    assert len(process.children()) == 0


@skip_unless_windows
def test_file_opener_produces_unlink_error(tmpdir, process):
    # FileOpener forces an error on Windows when we attempt to remove a file
    # The initial path may be deferred; which must be tested with an error
    path = tmpdir.joinpath('foo.txt')
    with open(path, 'w') as f:
        f.write('Hello\n')
    with FileOpener() as opener:
        opener.send(path)
        with pytest.raises(OSError):
            os.unlink(path)


@skip_unless_windows
def test_file_opener_produces_rmtree_error(tmpdir, process):
    subdir = tmpdir.joinpath('foo')
    os.mkdir(subdir)
    path = subdir.joinpath('bar.txt')
    with open(path, 'w') as f:
        f.write('Hello\n')
    with FileOpener(path):
        with pytest.raises(OSError):
            shutil.rmtree(subdir)
