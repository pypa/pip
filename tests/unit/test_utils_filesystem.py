import os
import shutil
from typing import Callable, Type

import pytest

from pip._internal.utils.filesystem import copy2_fixed, is_socket
from tests.lib.filesystem import make_socket_file, make_unreadable_file
from tests.lib.path import Path


def make_file(path: str) -> None:
    Path(path).touch()


def make_valid_symlink(path: str) -> None:
    target = path + "1"
    make_file(target)
    os.symlink(target, path)


def make_broken_symlink(path: str) -> None:
    os.symlink("foo", path)


def make_dir(path: str) -> None:
    os.mkdir(path)


skip_on_windows = pytest.mark.skipif("sys.platform == 'win32'")


@skip_on_windows
@pytest.mark.parametrize(
    "create,result",
    [
        (make_socket_file, True),
        (make_file, False),
        (make_valid_symlink, False),
        (make_broken_symlink, False),
        (make_dir, False),
    ],
)
def test_is_socket(create: Callable[[str], None], result: bool, tmpdir: Path) -> None:
    target = tmpdir.joinpath("target")
    create(target)
    assert os.path.lexists(target)
    assert is_socket(target) == result


@pytest.mark.parametrize(
    "create,error_type",
    [
        pytest.param(make_socket_file, shutil.SpecialFileError, marks=skip_on_windows),
        (make_unreadable_file, OSError),
    ],
)
def test_copy2_fixed_raises_appropriate_errors(
    create: Callable[[str], None], error_type: Type[Exception], tmpdir: Path
) -> None:
    src = tmpdir.joinpath("src")
    create(src)
    dest = tmpdir.joinpath("dest")

    with pytest.raises(error_type):
        copy2_fixed(src, dest)

    assert not dest.exists()
