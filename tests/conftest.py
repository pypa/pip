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
    path object instead of py.path.local.
    """
    name = request.node.name
    name = py.std.re.sub("[\W]", "_", name)
    tmp = request.config._tmpdirhandler.mktemp(name, numbered=True)
    return Path(tmp)


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
    shutil.copytree(SRC_DIR, pip_src,
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
