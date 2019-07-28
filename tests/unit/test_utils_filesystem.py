import os

import pytest

from pip._internal.utils.filesystem import is_socket

from ..lib.filesystem import make_socket_file
from ..lib.path import Path


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


@pytest.mark.skipif("sys.platform == 'win32'")
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
