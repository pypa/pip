import os
from pathlib import Path


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
