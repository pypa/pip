import itertools
import logging
import os
import shutil
import stat
import tempfile
import time

import pytest

from pip._internal.utils import temp_dir
from pip._internal.utils.misc import ensure_dir
from pip._internal.utils.temp_dir import (
    AdjacentTempDirectory,
    TempDirectory,
    global_tempdir_manager,
)
from tests.lib.filesystem import FileOpener


# No need to test symlinked directories on Windows
@pytest.mark.skipif("sys.platform == 'win32'")
def test_symlinked_path():
    with TempDirectory() as tmp_dir:
        assert os.path.exists(tmp_dir.path)

        alt_tmp_dir = tempfile.mkdtemp(prefix="pip-test-")
        assert (
            os.path.dirname(tmp_dir.path) ==
            os.path.dirname(os.path.realpath(alt_tmp_dir))
        )
        # are we on a system where /tmp is a symlink
        if os.path.realpath(alt_tmp_dir) != os.path.abspath(alt_tmp_dir):
            assert (
                os.path.dirname(tmp_dir.path) !=
                os.path.dirname(alt_tmp_dir)
            )
        else:
            assert (
                os.path.dirname(tmp_dir.path) ==
                os.path.dirname(alt_tmp_dir)
            )
        os.rmdir(tmp_dir.path)
        assert not os.path.exists(tmp_dir.path)


def test_deletes_readonly_files():
    def create_file(*args):
        fpath = os.path.join(*args)
        ensure_dir(os.path.dirname(fpath))
        with open(fpath, "w") as f:
            f.write("Holla!")

    def readonly_file(*args):
        fpath = os.path.join(*args)
        os.chmod(fpath, stat.S_IREAD)

    with TempDirectory() as tmp_dir:
        create_file(tmp_dir.path, "normal-file")
        create_file(tmp_dir.path, "readonly-file")
        readonly_file(tmp_dir.path, "readonly-file")

        create_file(tmp_dir.path, "subfolder", "normal-file")
        create_file(tmp_dir.path, "subfolder", "readonly-file")
        readonly_file(tmp_dir.path, "subfolder", "readonly-file")


def test_path_access_after_context_raises():
    with TempDirectory() as tmp_dir:
        path = tmp_dir.path

    with pytest.raises(AssertionError) as e:
        _ = tmp_dir.path

    assert path in str(e.value)


def test_path_access_after_clean_raises():
    tmp_dir = TempDirectory()
    path = tmp_dir.path
    tmp_dir.cleanup()

    with pytest.raises(AssertionError) as e:
        _ = tmp_dir.path

    assert path in str(e.value)


def test_create_and_cleanup_work():
    tmp_dir = TempDirectory()
    created_path = tmp_dir.path

    assert tmp_dir.path is not None
    assert os.path.exists(created_path)

    tmp_dir.cleanup()
    assert not os.path.exists(created_path)


@pytest.mark.parametrize("name", [
    "ABC",
    "ABC.dist-info",
    "_+-",
    "_package",
    "A......B",
    "AB",
    "A",
    "2",
])
def test_adjacent_directory_names(name):
    def names():
        return AdjacentTempDirectory._generate_names(name)

    chars = AdjacentTempDirectory.LEADING_CHARS

    # Ensure many names are unique
    # (For long *name*, this sequence can be extremely long.
    # However, since we're only ever going to take the first
    # result that works, provided there are many of those
    # and that shorter names result in totally unique sets,
    # it's okay to skip part of the test.)
    some_names = list(itertools.islice(names(), 1000))
    # We should always get at least 1000 names
    assert len(some_names) == 1000

    # Ensure original name does not appear early in the set
    assert name not in some_names

    if len(name) > 2:
        # Names should be at least 90% unique (given the infinite
        # range of inputs, and the possibility that generated names
        # may already exist on disk anyway, this is a much cheaper
        # criteria to enforce than complete uniqueness).
        assert len(some_names) > 0.9 * len(set(some_names))

        # Ensure the first few names are the same length as the original
        same_len = list(itertools.takewhile(
            lambda x: len(x) == len(name),
            some_names
        ))
        assert len(same_len) > 10

        # Check the first group are correct
        expected_names = ['~' + name[1:]]
        expected_names.extend('~' + c + name[2:] for c in chars)
        for x, y in zip(some_names, expected_names):
            assert x == y

    else:
        # All names are going to be longer than our original
        assert min(len(x) for x in some_names) > 1

        # All names are going to be unique
        assert len(some_names) == len(set(some_names))

        if len(name) == 2:
            # All but the first name are going to end with our original
            assert all(x.endswith(name) for x in some_names[1:])
        else:
            # All names are going to end with our original
            assert all(x.endswith(name) for x in some_names)


@pytest.mark.parametrize("name", [
    "A",
    "ABC",
    "ABC.dist-info",
    "_+-",
    "_package",
])
def test_adjacent_directory_exists(name, tmpdir):
    block_name, expect_name = itertools.islice(
        AdjacentTempDirectory._generate_names(name), 2)

    original = os.path.join(tmpdir, name)
    blocker = os.path.join(tmpdir, block_name)

    ensure_dir(original)
    ensure_dir(blocker)

    with AdjacentTempDirectory(original) as atmp_dir:
        assert expect_name == os.path.split(atmp_dir.path)[1]


def test_adjacent_directory_permission_error(monkeypatch):
    name = "ABC"

    def raising_mkdir(*args, **kwargs):
        raise OSError("Unknown OSError")

    with TempDirectory() as tmp_dir:
        original = os.path.join(tmp_dir.path, name)

        ensure_dir(original)
        monkeypatch.setattr("os.mkdir", raising_mkdir)

        with pytest.raises(OSError):
            with AdjacentTempDirectory(original):
                pass


def test_global_tempdir_manager():
    with global_tempdir_manager():
        d = TempDirectory(globally_managed=True)
        path = d.path
        assert os.path.exists(path)
    assert not os.path.exists(path)


def test_tempdirectory_asserts_global_tempdir(monkeypatch):
    monkeypatch.setattr(temp_dir, "_tempdir_manager", None)
    with pytest.raises(AssertionError):
        TempDirectory(globally_managed=True)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_temp_dir_warns_if_cannot_clean(caplog):
    temp_dir = TempDirectory()
    temp_dir_path = temp_dir.path

    stime = time.time()

    # Capture only at WARNING level and up
    with caplog.at_level(logging.WARNING, 'pip._internal.utils.temp_dir'):
        # open a file within the temporary directory in a sub-process
        with FileOpener() as opener:
            subpath = os.path.join(temp_dir_path, 'foo.txt')
            with open(subpath, 'w') as f:
                f.write('Cannot be deleted')
            opener.send(subpath)
            # with the file open, attempt to remove the log directory
            temp_dir.cleanup()

        # assert that a WARNING was logged about virus scanner
        assert 'WARNING' in caplog.text
        assert 'virus scanner' in caplog.text

    # Assure that the cleanup was properly retried
    duration = time.time() - stime
    assert duration >= 2.0

    # Clean-up for failed TempDirectory cleanup
    shutil.rmtree(temp_dir_path, ignore_errors=True)
