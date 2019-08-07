import os
import shutil

import pytest

from pip._internal.utils.filesystem import copytree, is_socket

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


@pytest.mark.skipif("sys.platform == 'win32'")
def test_copytree_maps_socket_errors(tmpdir):
    src_dir = tmpdir.joinpath("src")
    make_dir(src_dir)
    make_file(src_dir.joinpath("a"))
    socket_src = src_dir.joinpath("b")
    make_socket_file(socket_src)
    make_file(src_dir.joinpath("c"))

    dest_dir = tmpdir.joinpath("dest")
    socket_dest = dest_dir.joinpath("b")

    with pytest.raises(shutil.Error) as e:
        copytree(src_dir, dest_dir)

    errors = e.value.args[0]
    assert len(errors) == 1
    src, dest, error = errors[0]
    assert src == str(socket_src)
    assert dest == str(socket_dest)
    assert isinstance(error, shutil.SpecialFileError)

    assert dest_dir.joinpath("a").exists()
    assert not socket_dest.exists()
    assert dest_dir.joinpath("c").exists()
