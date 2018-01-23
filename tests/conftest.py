import io
import os
import shutil
import subprocess
import sys

import pytest
import six

import pip._internal
from tests.lib import SRC_DIR, TestData
from tests.lib.path import Path
from tests.lib.scripttest import PipTestEnvironment
from tests.lib.venv import VirtualEnvironment


def pytest_collection_modifyitems(items):
    for item in items:
        if not hasattr(item, 'module'):  # e.g.: DoctestTextfile
            continue

        # Mark network tests as flaky
        if item.get_marker('network') is not None and "CI" in os.environ:
            item.add_marker(pytest.mark.flaky(reruns=3))

        module_path = os.path.relpath(
            item.module.__file__,
            os.path.commonprefix([__file__, item.module.__file__]),
        )

        module_root_dir = module_path.split(os.pathsep)[0]
        if (module_root_dir.startswith("functional") or
                module_root_dir.startswith("integration") or
                module_root_dir.startswith("lib")):
            item.add_marker(pytest.mark.integration)
        elif module_root_dir.startswith("unit"):
            item.add_marker(pytest.mark.unit)

            # We don't want to allow using the script resource if this is a
            # unit test, as unit tests should not need all that heavy lifting
            if set(getattr(item, "funcargnames", [])) & {"script"}:
                raise RuntimeError(
                    "Cannot use the ``script`` funcarg in a unit test: "
                    "(filename = {}, item = {})".format(module_path, item)
                )
        else:
            raise RuntimeError(
                "Unknown test type (filename = {})".format(module_path)
            )


@pytest.yield_fixture
def tmpdir(tmpdir):
    """
    Return a temporary directory path object which is unique to each test
    function invocation, created as a sub directory of the base temporary
    directory. The returned object is a ``tests.lib.path.Path`` object.

    This uses the built-in tmpdir fixture from pytest itself but modified
    to return our typical path object instead of py.path.local as well as
    deleting the temporary directories at the end of each test case.
    """
    assert tmpdir.isdir()
    yield Path(str(tmpdir))
    # Clear out the temporary directory after the test has finished using it.
    # This should prevent us from needing a multiple gigabyte temporary
    # directory while running the tests.
    tmpdir.remove(ignore_errors=True)


@pytest.fixture(autouse=True)
def isolate(tmpdir):
    """
    Isolate our tests so that things like global configuration files and the
    like do not affect our test results.

    We use an autouse function scoped fixture because we want to ensure that
    every test has it's own isolated home directory.
    """

    # TODO: Figure out how to isolate from *system* level configuration files
    #       as well as user level configuration files.

    # Create a directory to use as our home location.
    home_dir = os.path.join(str(tmpdir), "home")
    os.makedirs(home_dir)

    # Create a directory to use as a fake root
    fake_root = os.path.join(str(tmpdir), "fake-root")
    os.makedirs(fake_root)

    if sys.platform == 'win32':
        # Note: this will only take effect in subprocesses...
        home_drive, home_path = os.path.splitdrive(home_dir)
        os.environ.update({
            'USERPROFILE': home_dir,
            'HOMEDRIVE': home_drive,
            'HOMEPATH': home_path,
        })
        for env_var, sub_path in (
            ('APPDATA', 'AppData/Roaming'),
            ('LOCALAPPDATA', 'AppData/Local'),
        ):
            path = os.path.join(home_dir, *sub_path.split('/'))
            os.environ[env_var] = path
            os.makedirs(path)
    else:
        # Set our home directory to our temporary directory, this should force
        # all of our relative configuration files to be read from here instead
        # of the user's actual $HOME directory.
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

    # We want to disable the version check from running in the tests
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "true"

    # FIXME: Windows...
    os.makedirs(os.path.join(home_dir, ".config", "git"))
    with open(os.path.join(home_dir, ".config", "git", "config"), "wb") as fp:
        fp.write(
            b"[user]\n\tname = pip\n\temail = pypa-dev@googlegroups.com\n"
        )


@pytest.yield_fixture(scope='session')
def virtualenv_template(tmpdir_factory):
    tmpdir = Path(str(tmpdir_factory.mktemp('virtualenv')))
    # Copy over our source tree so that each virtual environment is self
    # contained
    pip_src = tmpdir.join("pip_src").abspath
    shutil.copytree(
        SRC_DIR,
        pip_src,
        ignore=shutil.ignore_patterns(
            "*.pyc", "__pycache__", "contrib", "docs", "tasks", "*.txt",
            "tests", "pip.egg-info", "build", "dist", ".tox", ".git",
        ),
    )
    # Create the virtual environment
    venv = VirtualEnvironment.create(
        tmpdir.join("venv_orig"),
        pip_source_dir=pip_src,
        relocatable=True,
    )
    if sys.platform == 'win32':
        # Work around setuptools' easy_install.exe
        # not working properly after relocation.
        for exe in os.listdir(venv.bin):
            if exe.startswith('easy_install'):
                (venv.bin / exe).remove()
        with open(venv.bin / 'easy_install.bat', 'w') as fp:
            fp.write('python.exe -m easy_install %*\n')

    # Rename original virtualenv directory to make sure
    # it's not reused by mistake from one of the copies.
    venv_template = tmpdir / "venv_template"
    os.rename(venv.location, venv_template)
    yield venv_template
    tmpdir.rmtree(noerrors=True)


@pytest.yield_fixture
def virtualenv(virtualenv_template, tmpdir, isolate):
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    venv_location = tmpdir.join("workspace", "venv")
    shutil.copytree(virtualenv_template, venv_location, symlinks=True)
    venv = VirtualEnvironment(venv_location)
    yield venv
    venv_location.rmtree(noerrors=True)


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


@pytest.fixture(scope="session")
def common_wheels(tmpdir_factory):
    """Provide a directory with latest setuptools and wheel wheels"""
    wheels_dir = tmpdir_factory.mktemp('common_wheels')
    subprocess.check_call([
        'pip', 'download', 'wheel', 'setuptools',
        '-d', str(wheels_dir),
    ])
    yield wheels_dir
    wheels_dir.remove(ignore_errors=True)


@pytest.fixture
def data(tmpdir):
    return TestData.copy(tmpdir.join("data"))


class InMemoryPipResult(object):
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


class InMemoryPip(object):
    def pip(self, *args):
        orig_stdout = sys.stdout
        if six.PY3:
            stdout = io.StringIO()
        else:
            stdout = io.BytesIO()
        sys.stdout = stdout
        try:
            returncode = pip._internal.main(list(args))
        except SystemExit as e:
            returncode = e.code or 0
        finally:
            sys.stdout = orig_stdout
        return InMemoryPipResult(returncode, stdout.getvalue())


@pytest.fixture
def in_memory_pip():
    return InMemoryPip()
