import os
import shutil
import subprocess
import sys
import tempfile

import py
import pytest

from tests.lib import TestData
from tests.lib.path import Path
from tests.lib.scripttest import PipTestEnvironment
from tests.lib.venv import VirtualEnvironment

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, "wb")


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


@pytest.fixture(scope="session")
def wheel_dir(request):
    wheel_dir = tempfile.mkdtemp()

    @request.addfinalizer
    def finalize():
        shutil.rmtree(wheel_dir, ignore_errors=True)

    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--dist-dir", wheel_dir],
        stderr=subprocess.STDOUT,
        stdout=DEVNULL,
    )

    return wheel_dir


@pytest.fixture
def virtualenv(wheel_dir, tmpdir, monkeypatch):
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    # Force shutil to use the older method of rmtree that didn't use the fd
    # functions. These seem to fail on Travis (and only on Travis).
    monkeypatch.setattr(shutil, "_use_fd_functions", False, raising=False)

    # Create the virtual environment
    venv = VirtualEnvironment.create(
        tmpdir.join("workspace", "venv"),
        wheel_dir=wheel_dir,
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
