import os
import shutil

import py
import pytest

from tests.lib import SRC_DIR, TestData
from tests.lib.path import Path
from tests.lib.scripttest import PipTestEnvironment
from tests.lib.venv import VirtualEnvironment


@pytest.fixture
def tmpdir(request):
    """
    Return a temporary directory path object which is unique to each test
    function invocation, created as a sub directory of the base temporary
    directory. The returned object is a ``tests.lib.path.Path`` object.

    This is taken from pytest itself but modified to return our typical
    path object instead of py.path.local as well as deleting the temporary
    directories at the end of each test case.
    """
    name = request.node.name
    name = py.std.re.sub("[\W]", "_", name)
    tmp = request.config._tmpdirhandler.mktemp(name, numbered=True)

    # Clear out the temporary directory after the test has finished using it.
    # This should prevent us from needing a multiple gigabyte temporary
    # directory while running the tests.
    request.addfinalizer(lambda: shutil.rmtree(str(tmp), ignore_errors=True))

    return Path(str(tmp))


@pytest.fixture(autouse=True)
def isolate(tmpdir):
    """
    Isolate our tests so that things like global configuration files and the
    like do not affect our test results.

    We use an autouse function scoped fixture because we want to ensure that
    every test has it's own isolated home directory.
    """
    # TODO: Ensure Windows will respect $HOME, including for the cache
    #       directory

    # TODO: Figure out how to isolate from *system* level configuration files
    #       as well as user level configuration files.

    # Create a directory to use as our home location.
    home_dir = os.path.join(str(tmpdir), "home")
    os.makedirs(home_dir)

    # Create a directory to use as a fake root
    fake_root = os.path.join(str(tmpdir), "fake-root")
    os.makedirs(fake_root)

    # Set our home directory to our temporary directory, this should force all
    # of our relative configuration files to be read from here instead of the
    # user's actual $HOME directory.
    os.environ["HOME"] = home_dir

    # Isolate ourselves from XDG directories
    os.environ["XDG_DATA_HOME"] = os.path.join(home_dir, ".local", "share")
    os.environ["XDG_CONFIG_HOME"] = os.path.join(home_dir, ".config")
    os.environ["XDG_CACHE_HOME"] = os.path.join(home_dir, ".cache")
    os.environ["XDG_RUNTIME_DIR"] = os.path.join(home_dir, ".runtime")
    os.environ["XDG_DATA_DIRS"] = ":".join([
        os.path.join(fake_root, "usr", "local", "share"),
        os.path.join(fake_root, "usr", "share"),
    ])
    os.environ["XDG_CONFIG_DIRS"] = os.path.join(fake_root, "etc", "xdg")

    # Configure git, because without an author name/email git will complain
    # and cause test failures.
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    os.environ["GIT_AUTHOR_NAME"] = "pip"
    os.environ["GIT_AUTHOR_EMAIL"] = "pypa-dev@googlegroups.com"

    os.makedirs(os.path.join(home_dir, ".config", "git"))
    with open(os.path.join(home_dir, ".config", "git", "config"), "wb") as fp:
        fp.write(
            b"[user]\n\tname = pip\n\temail = pypa-dev@googlegroups.com\n"
        )


@pytest.fixture
def virtualenv(tmpdir, monkeypatch):
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    # Force shutil to use the older method of rmtree that didn't use the fd
    # functions. These seem to fail on Travis (and only on Travis).
    monkeypatch.setattr(shutil, "_use_fd_functions", False, raising=False)

    # Copy over our source tree so that each virtual environment is self
    # contained
    pip_src = tmpdir.join("pip_src").abspath
    shutil.copytree(
        SRC_DIR,
        pip_src,
        ignore=shutil.ignore_patterns(
            "*.pyc", "tests", "pip.egg-info", "build", "dist", ".tox",
        ),
    )

    # Create the virtual environment
    venv = VirtualEnvironment.create(
        tmpdir.join("workspace", "venv"),
        pip_source_dir=pip_src,
    )

    # Undo our monkeypatching of shutil
    monkeypatch.undo()

    return venv


@pytest.fixture
def script(tmpdir, virtualenv):
    """
    Return a PipTestEnvironment which is unique to each test function and
    will execute all commands inside of the unique virtual environment for this
    test function. The returned object is a
    ``tests.lib.scripttest.PipTestEnvironment``.
    """
    return PipTestEnvironment(
        # The base location for our test environment
        tmpdir.join("workspace"),

        # Tell the Test Environment where our virtualenv is located
        virtualenv=virtualenv.location,

        # Do not ignore hidden files, they need to be checked as well
        ignore_hidden=False,

        # We are starting with an already empty directory
        start_clear=False,

        # We want to ensure no temporary files are left behind, so the
        # PipTestEnvironment needs to capture and assert against temp
        capture_temp=True,
        assert_no_temp=True,
    )


@pytest.fixture
def data(tmpdir):
    return TestData.copy(tmpdir.join("data"))
