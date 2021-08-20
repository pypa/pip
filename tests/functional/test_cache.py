import os
import shutil
from glob import glob

import pytest


@pytest.fixture
def cache_dir(script):
    result = script.run(
        "python",
        "-c",
        "from pip._internal.locations import USER_CACHE_DIR;print(USER_CACHE_DIR)",
    )
    return result.stdout.strip()


@pytest.fixture
def http_cache_dir(cache_dir):
    return os.path.normcase(os.path.join(cache_dir, "http"))


@pytest.fixture
def wheel_cache_dir(cache_dir):
    return os.path.normcase(os.path.join(cache_dir, "wheels"))


@pytest.fixture
def http_cache_files(http_cache_dir):
    destination = os.path.join(http_cache_dir, "arbitrary", "pathname")

    if not os.path.exists(destination):
        return []

    filenames = glob(os.path.join(destination, "*"))
    files = []
    for filename in filenames:
        files.append(os.path.join(destination, filename))
    return files


@pytest.fixture
def wheel_cache_files(wheel_cache_dir):
    destination = os.path.join(wheel_cache_dir, "arbitrary", "pathname")

    if not os.path.exists(destination):
        return []

    filenames = glob(os.path.join(destination, "*.whl"))
    files = []
    for filename in filenames:
        files.append(os.path.join(destination, filename))
    return files


@pytest.fixture
def populate_http_cache(http_cache_dir):
    destination = os.path.join(http_cache_dir, "arbitrary", "pathname")
    os.makedirs(destination)

    files = [
        ("aaaaaaaaa", os.path.join(destination, "aaaaaaaaa")),
        ("bbbbbbbbb", os.path.join(destination, "bbbbbbbbb")),
        ("ccccccccc", os.path.join(destination, "ccccccccc")),
    ]

    for _name, filename in files:
        with open(filename, "w"):
            pass

    return files


@pytest.fixture
def populate_wheel_cache(wheel_cache_dir):
    destination = os.path.join(wheel_cache_dir, "arbitrary", "pathname")
    os.makedirs(destination)

    files = [
        ("yyy-1.2.3", os.path.join(destination, "yyy-1.2.3-py3-none-any.whl")),
        ("zzz-4.5.6", os.path.join(destination, "zzz-4.5.6-py3-none-any.whl")),
        ("zzz-4.5.7", os.path.join(destination, "zzz-4.5.7-py3-none-any.whl")),
        ("zzz-7.8.9", os.path.join(destination, "zzz-7.8.9-py3-none-any.whl")),
    ]

    for _name, filename in files:
        with open(filename, "w"):
            pass

    return files


@pytest.fixture
def empty_wheel_cache(wheel_cache_dir):
    if os.path.exists(wheel_cache_dir):
        shutil.rmtree(wheel_cache_dir)


def list_matches_wheel(wheel_name, result):
    """Returns True if any line in `result`, which should be the output of
    a `pip cache list` call, matches `wheel_name`.

    E.g., If wheel_name is `foo-1.2.3` it searches for a line starting with
          `- foo-1.2.3-py3-none-any.whl `."""
    lines = result.stdout.splitlines()
    expected = f" - {wheel_name}-py3-none-any.whl "
    return any(map(lambda l: l.startswith(expected), lines))


def list_matches_wheel_abspath(wheel_name, result):
    """Returns True if any line in `result`, which should be the output of
    a `pip cache list --format=abspath` call, is a valid path and belongs to
    `wheel_name`.

    E.g., If wheel_name is `foo-1.2.3` it searches for a line starting with
          `foo-1.2.3-py3-none-any.whl`."""
    lines = result.stdout.splitlines()
    expected = f"{wheel_name}-py3-none-any.whl"
    return any(
        map(
            lambda l: os.path.basename(l).startswith(expected) and os.path.exists(l),
            lines,
        )
    )


@pytest.fixture
def remove_matches_http(http_cache_dir):
    """Returns True if any line in `result`, which should be the output of
    a `pip cache purge` call, matches `http_filename`.

    E.g., If http_filename is `aaaaaaaaa`, it searches for a line equal to
    `Removed <http files cache dir>/arbitrary/pathname/aaaaaaaaa`.
    """

    def _remove_matches_http(http_filename, result):
        lines = result.stdout.splitlines()

        # The "/arbitrary/pathname/" bit is an implementation detail of how
        # the `populate_http_cache` fixture is implemented.
        path = os.path.join(
            http_cache_dir,
            "arbitrary",
            "pathname",
            http_filename,
        )
        expected = f"Removed {path}"
        return expected in lines

    return _remove_matches_http


@pytest.fixture
def remove_matches_wheel(wheel_cache_dir):
    """Returns True if any line in `result`, which should be the output of
    a `pip cache remove`/`pip cache purge` call, matches `wheel_name`.

    E.g., If wheel_name is `foo-1.2.3`, it searches for a line equal to
    `Removed <wheel cache dir>/arbitrary/pathname/foo-1.2.3-py3-none-any.whl`.
    """

    def _remove_matches_wheel(wheel_name, result):
        lines = result.stdout.splitlines()

        wheel_filename = f"{wheel_name}-py3-none-any.whl"

        # The "/arbitrary/pathname/" bit is an implementation detail of how
        # the `populate_wheel_cache` fixture is implemented.
        path = os.path.join(
            wheel_cache_dir,
            "arbitrary",
            "pathname",
            wheel_filename,
        )
        expected = f"Removed {path}"
        return expected in lines

    return _remove_matches_wheel


def test_cache_dir(script, cache_dir):
    result = script.pip("cache", "dir")

    assert os.path.normcase(cache_dir) == result.stdout.strip()


def test_cache_dir_too_many_args(script, cache_dir):
    result = script.pip("cache", "dir", "aaa", expect_error=True)

    assert result.stdout == ""

    # This would be `result.stderr == ...`, but pip prints deprecation
    # warnings on Python 2.7, so we check if the _line_ is in stderr.
    assert "ERROR: Too many arguments" in result.stderr.splitlines()


@pytest.mark.usefixtures("populate_http_cache", "populate_wheel_cache")
def test_cache_info(script, http_cache_dir, wheel_cache_dir, wheel_cache_files):
    result = script.pip("cache", "info")

    assert f"Package index page cache location: {http_cache_dir}" in result.stdout
    assert f"Wheels location: {wheel_cache_dir}" in result.stdout
    num_wheels = len(wheel_cache_files)
    assert f"Number of wheels: {num_wheels}" in result.stdout


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list(script):
    """Running `pip cache list` should return exactly what the
    populate_wheel_cache fixture adds."""
    result = script.pip("cache", "list")

    assert list_matches_wheel("yyy-1.2.3", result)
    assert list_matches_wheel("zzz-4.5.6", result)
    assert list_matches_wheel("zzz-4.5.7", result)
    assert list_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_abspath(script):
    """Running `pip cache list --format=abspath` should return full
    paths of exactly what the populate_wheel_cache fixture adds."""
    result = script.pip("cache", "list", "--format=abspath")

    assert list_matches_wheel_abspath("yyy-1.2.3", result)
    assert list_matches_wheel_abspath("zzz-4.5.6", result)
    assert list_matches_wheel_abspath("zzz-4.5.7", result)
    assert list_matches_wheel_abspath("zzz-7.8.9", result)


@pytest.mark.usefixtures("empty_wheel_cache")
def test_cache_list_with_empty_cache(script):
    """Running `pip cache list` with an empty cache should print
    "Nothing cached." and exit."""
    result = script.pip("cache", "list")
    assert result.stdout == "Nothing cached.\n"


@pytest.mark.usefixtures("empty_wheel_cache")
def test_cache_list_with_empty_cache_abspath(script):
    """Running `pip cache list --format=abspath` with an empty cache should not
    print anything and exit."""
    result = script.pip("cache", "list", "--format=abspath")
    assert result.stdout.strip() == ""


def test_cache_list_too_many_args(script):
    """Passing `pip cache list` too many arguments should cause an error."""
    script.pip("cache", "list", "aaa", "bbb", expect_error=True)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_name_match(script):
    """Running `pip cache list zzz` should list zzz-4.5.6, zzz-4.5.7,
    zzz-7.8.9, but nothing else."""
    result = script.pip("cache", "list", "zzz", "--verbose")

    assert not list_matches_wheel("yyy-1.2.3", result)
    assert list_matches_wheel("zzz-4.5.6", result)
    assert list_matches_wheel("zzz-4.5.7", result)
    assert list_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_name_match_abspath(script):
    """Running `pip cache list zzz --format=abspath` should list paths of
    zzz-4.5.6, zzz-4.5.7, zzz-7.8.9, but nothing else."""
    result = script.pip("cache", "list", "zzz", "--format=abspath", "--verbose")

    assert not list_matches_wheel_abspath("yyy-1.2.3", result)
    assert list_matches_wheel_abspath("zzz-4.5.6", result)
    assert list_matches_wheel_abspath("zzz-4.5.7", result)
    assert list_matches_wheel_abspath("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_name_and_version_match(script):
    """Running `pip cache list zzz-4.5.6` should list zzz-4.5.6, but
    nothing else."""
    result = script.pip("cache", "list", "zzz-4.5.6", "--verbose")

    assert not list_matches_wheel("yyy-1.2.3", result)
    assert list_matches_wheel("zzz-4.5.6", result)
    assert not list_matches_wheel("zzz-4.5.7", result)
    assert not list_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_name_and_version_match_abspath(script):
    """Running `pip cache list zzz-4.5.6 --format=abspath` should list path of
    zzz-4.5.6, but nothing else."""
    result = script.pip("cache", "list", "zzz-4.5.6", "--format=abspath", "--verbose")

    assert not list_matches_wheel_abspath("yyy-1.2.3", result)
    assert list_matches_wheel_abspath("zzz-4.5.6", result)
    assert not list_matches_wheel_abspath("zzz-4.5.7", result)
    assert not list_matches_wheel_abspath("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_remove_no_arguments(script):
    """Running `pip cache remove` with no arguments should cause an error."""
    script.pip("cache", "remove", expect_error=True)


def test_cache_remove_too_many_args(script):
    """Passing `pip cache remove` too many arguments should cause an error."""
    script.pip("cache", "remove", "aaa", "bbb", expect_error=True)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_remove_name_match(script, remove_matches_wheel):
    """Running `pip cache remove zzz` should remove zzz-4.5.6 and zzz-7.8.9,
    but nothing else."""
    result = script.pip("cache", "remove", "zzz", "--verbose")

    assert not remove_matches_wheel("yyy-1.2.3", result)
    assert remove_matches_wheel("zzz-4.5.6", result)
    assert remove_matches_wheel("zzz-4.5.7", result)
    assert remove_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_remove_name_and_version_match(script, remove_matches_wheel):
    """Running `pip cache remove zzz-4.5.6` should remove zzz-4.5.6, but
    nothing else."""
    result = script.pip("cache", "remove", "zzz-4.5.6", "--verbose")

    assert not remove_matches_wheel("yyy-1.2.3", result)
    assert remove_matches_wheel("zzz-4.5.6", result)
    assert not remove_matches_wheel("zzz-4.5.7", result)
    assert not remove_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_http_cache", "populate_wheel_cache")
def test_cache_purge(script, remove_matches_http, remove_matches_wheel):
    """Running `pip cache purge` should remove all cached http files and
    wheels."""
    result = script.pip("cache", "purge", "--verbose")

    assert remove_matches_http("aaaaaaaaa", result)
    assert remove_matches_http("bbbbbbbbb", result)
    assert remove_matches_http("ccccccccc", result)

    assert remove_matches_wheel("yyy-1.2.3", result)
    assert remove_matches_wheel("zzz-4.5.6", result)
    assert remove_matches_wheel("zzz-4.5.7", result)
    assert remove_matches_wheel("zzz-7.8.9", result)


@pytest.mark.usefixtures("populate_http_cache", "populate_wheel_cache")
def test_cache_purge_too_many_args(script, http_cache_files, wheel_cache_files):
    """Running `pip cache purge aaa` should raise an error and remove no
    cached http files or wheels."""
    result = script.pip("cache", "purge", "aaa", "--verbose", expect_error=True)
    assert result.stdout == ""

    # This would be `result.stderr == ...`, but pip prints deprecation
    # warnings on Python 2.7, so we check if the _line_ is in stderr.
    assert "ERROR: Too many arguments" in result.stderr.splitlines()

    # Make sure nothing was deleted.
    for filename in http_cache_files + wheel_cache_files:
        assert os.path.exists(filename)


@pytest.mark.parametrize("command", ["info", "list", "remove", "purge"])
def test_cache_abort_when_no_cache_dir(script, command):
    """Running any pip cache command when cache is disabled should
    abort and log an informative error"""
    result = script.pip("cache", command, "--no-cache-dir", expect_error=True)
    assert result.stdout == ""

    assert (
        "ERROR: pip cache commands can not function"
        " since cache is disabled." in result.stderr.splitlines()
    )
