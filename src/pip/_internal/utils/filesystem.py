from __future__ import annotations

import fnmatch
import os
import os.path
import random
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, cast

from pip._internal.utils.compat import get_path_uid
from pip._internal.utils.misc import format_size
from pip._internal.utils.retry import retry


def check_path_owner(path: str) -> bool:
    # If we don't have a way to check the effective uid of this process, then
    # we'll just assume that we own the directory.
    if sys.platform == "win32" or not hasattr(os, "geteuid"):
        return True

    assert os.path.isabs(path)

    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Check if path is writable by current user.
            if os.geteuid() == 0:
                # Special handling for root user in order to handle properly
                # cases where users use sudo without -H flag.
                try:
                    path_uid = get_path_uid(path)
                except OSError:
                    return False
                return path_uid == 0
            else:
                return os.access(path, os.W_OK)
        else:
            previous, path = path, os.path.dirname(path)
    return False  # assume we don't own the path


@contextmanager
def adjacent_tmp_file(path: str, **kwargs: Any) -> Generator[BinaryIO, None, None]:
    """Return a file-like object pointing to a tmp file next to path.

    The file is created securely and is ensured to be written to disk
    after the context reaches its end.

    kwargs will be passed to tempfile.NamedTemporaryFile to control
    the way the temporary file will be opened.
    """
    with NamedTemporaryFile(
        delete=False,
        dir=os.path.dirname(path),
        prefix=os.path.basename(path),
        suffix=".tmp",
        **kwargs,
    ) as f:
        result = cast(BinaryIO, f)
        try:
            yield result
        finally:
            result.flush()
            os.fsync(result.fileno())


replace = retry(stop_after_delay=1, wait=0.25)(os.replace)


# test_writable_dir and _test_writable_dir_win are copied from Flit,
# with the author's agreement to also place them under pip's license.
def test_writable_dir(path: str) -> bool:
    """Check if a directory is writable.

    Uses os.access() on POSIX, tries creating files on Windows.
    """
    # If the directory doesn't exist, find the closest parent that does.
    while not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break  # Should never get here, but infinite loops are bad
        path = parent

    if os.name == "posix":
        return os.access(path, os.W_OK)

    return _test_writable_dir_win(path)


def _test_writable_dir_win(path: str) -> bool:
    # os.access doesn't work on Windows: http://bugs.python.org/issue2528
    # and we can't use tempfile: http://bugs.python.org/issue22107
    basename = "accesstest_deleteme_fishfingers_custard_"
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(10):
        name = basename + "".join(random.choice(alphabet) for _ in range(6))
        file = os.path.join(path, name)
        try:
            fd = os.open(file, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            pass
        except PermissionError:
            # This could be because there's a directory with the same name.
            # But it's highly unlikely there's a directory called that,
            # so we'll assume it's because the parent dir is not writable.
            # This could as well be because the parent dir is not readable,
            # due to non-privileged user access.
            return False
        else:
            os.close(fd)
            os.unlink(file)
            return True

    # This should never be reached
    raise OSError("Unexpected condition testing for writable directory")


def find_files(path: str, pattern: str) -> list[str]:
    """Returns a list of absolute paths of files beneath path, recursively,
    with filenames which match the UNIX-style shell glob pattern."""
    result: list[str] = []
    for root, _, files in os.walk(path):
        matches = fnmatch.filter(files, pattern)
        result.extend(os.path.join(root, f) for f in matches)
    return result


def file_size(path: str) -> int | float:
    # If it's a symlink, return 0.
    if os.path.islink(path):
        return 0
    return os.path.getsize(path)


def format_file_size(path: str) -> str:
    return format_size(file_size(path))


def directory_size(path: str) -> int | float:
    size = 0.0
    for root, _dirs, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            size += file_size(file_path)
    return size


def format_directory_size(path: str) -> str:
    return format_size(directory_size(path))


def copy_directory_permissions(directory: str, target_file: BinaryIO) -> None:
    mode = (
        os.stat(directory).st_mode & 0o666  # select read/write permissions of directory
        | 0o600  # set owner read/write permissions
    )
    # Change permissions only if there is no risk of following a symlink.
    if os.chmod in os.supports_fd:
        os.chmod(target_file.fileno(), mode)
    elif os.chmod in os.supports_follow_symlinks:
        os.chmod(target_file.name, mode, follow_symlinks=False)


def subdirs_without_files(path: str) -> Generator[Path]:
    """Yields every subdirectory of +path+ that has no files under it."""

    def inner(path: Path, parents: list[Path]) -> Generator[Path]:
        path_obj = Path(path)

        if not path_obj.exists():
            return

        subdirs = []
        for item in path_obj.iterdir():
            if item.is_dir():
                subdirs.append(item)
            else:
                # If we find a file, we want to preserve the whole subtree,
                # so bail immediately.
                return

        # If we get to this point, we didn't find a file yet.

        if parents is None:
            parents = []
        else:
            parents += [path_obj]

        if subdirs:
            for subdir in subdirs:
                yield from inner(subdir, parents)
        else:
            yield from parents

    yield from sorted(set(inner(Path(path), [])), reverse=True)


def subdirs_without_wheels(path: str) -> Generator[Path]:
    """Yields every subdirectory of +path+ that has no .whl files under it."""

    def inner(path: str | Path, parents: list[Path]) -> Generator[Path]:
        path_obj = Path(path)

        if not path_obj.exists():
            return

        subdirs = []
        for item in path_obj.iterdir():
            if item.is_dir():
                subdirs.append(item)
            elif item.name.endswith(".whl"):
                # If we found a wheel, we want to preserve this whole subtree,
                # so we bail immediately and don't return any results.
                return

        # If we get to this point, we didn't find a wheel yet.

        if parents is None:
            parents = []
        else:
            parents += [path_obj]

        if subdirs:
            for subdir in subdirs:
                yield from inner(subdir, parents)
        else:
            yield from parents

    yield from sorted(set(inner(path, [])), reverse=True)
