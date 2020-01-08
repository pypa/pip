import compileall
import fnmatch
import io
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager

import pytest
import six
from pip._vendor.contextlib2 import ExitStack
from setuptools.wheel import Wheel

from pip._internal.cli.main import main as pip_entry_point
from pip._internal.utils.temp_dir import global_tempdir_manager
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from tests.lib import DATA_DIR, SRC_DIR, TestData
from tests.lib.certs import make_tls_cert, serialize_cert, serialize_key
from tests.lib.path import Path
from tests.lib.scripttest import PipTestEnvironment
from tests.lib.server import make_mock_server, server_running
from tests.lib.venv import VirtualEnvironment

if MYPY_CHECK_RUNNING:
    from typing import Dict, Iterable

    from tests.lib.server import MockServer as _MockServer, Responder


def pytest_addoption(parser):
    parser.addoption(
        "--keep-tmpdir", action="store_true",
        default=False, help="keep temporary test directories"
    )
    parser.addoption("--use-venv", action="store_true",
                     help="use venv for virtual environment creation")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if not hasattr(item, 'module'):  # e.g.: DoctestTextfile
            continue

        # Mark network tests as flaky
        if (item.get_closest_marker('network') is not None and
                "CI" in os.environ):
            item.add_marker(pytest.mark.flaky(reruns=3))

        if six.PY3:
            if (item.get_closest_marker('incompatible_with_test_venv') and
                    config.getoption("--use-venv")):
                item.add_marker(pytest.mark.skip(
                    'Incompatible with test venv'))
            if (item.get_closest_marker('incompatible_with_venv') and
                    sys.prefix != sys.base_prefix):
                item.add_marker(pytest.mark.skip(
                    'Incompatible with venv'))

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
        else:
            raise RuntimeError(
                "Unknown test type (filename = {})".format(module_path)
            )


@pytest.fixture(scope='session')
def tmpdir_factory(request, tmpdir_factory):
    """ Modified `tmpdir_factory` session fixture
    that will automatically cleanup after itself.
    """
    yield tmpdir_factory
    if not request.config.getoption("--keep-tmpdir"):
        tmpdir_factory.getbasetemp().remove(ignore_errors=True)


@pytest.fixture
def tmpdir(request, tmpdir):
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
    if not request.config.getoption("--keep-tmpdir"):
        shutil.rmtree(six.text_type(tmpdir), ignore_errors=True)


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

    # Make sure tests don't share a requirements tracker.
    os.environ.pop('PIP_REQ_TRACKER', None)

    # FIXME: Windows...
    os.makedirs(os.path.join(home_dir, ".config", "git"))
    with open(os.path.join(home_dir, ".config", "git", "config"), "wb") as fp:
        fp.write(
            b"[user]\n\tname = pip\n\temail = pypa-dev@googlegroups.com\n"
        )


@pytest.fixture(autouse=True)
def scoped_global_tempdir_manager():
    """Make unit tests with globally-managed tempdirs easier

    Each test function gets its own individual scope for globally-managed
    temporary directories in the application.
    """
    with global_tempdir_manager():
        yield


@pytest.fixture(scope='session')
def pip_src(tmpdir_factory):
    def not_code_files_and_folders(path, names):
        # In the root directory...
        if path == SRC_DIR:
            # ignore all folders except "src"
            folders = {name for name in names if os.path.isdir(path / name)}
            to_ignore = folders - {"src"}
            # and ignore ".git" if present (which may be a file if in a linked
            # worktree).
            if ".git" in names:
                to_ignore.add(".git")
            return to_ignore

        # Ignore all compiled files and egg-info.
        ignored = set()
        for pattern in ("__pycache__", "*.pyc", "pip.egg-info"):
            ignored.update(fnmatch.filter(names, pattern))
        return ignored

    pip_src = Path(str(tmpdir_factory.mktemp('pip_src'))).joinpath('pip_src')
    # Copy over our source tree so that each use is self contained
    shutil.copytree(
        SRC_DIR,
        pip_src.resolve(),
        ignore=not_code_files_and_folders,
    )
    return pip_src


def _common_wheel_editable_install(tmpdir_factory, common_wheels, package):
    wheel_candidates = list(common_wheels.glob('%s-*.whl' % package))
    assert len(wheel_candidates) == 1, wheel_candidates
    install_dir = Path(str(tmpdir_factory.mktemp(package))) / 'install'
    Wheel(wheel_candidates[0]).install_as_egg(install_dir)
    (install_dir / 'EGG-INFO').rename(install_dir / '%s.egg-info' % package)
    assert compileall.compile_dir(str(install_dir), quiet=1)
    return install_dir


@pytest.fixture(scope='session')
def setuptools_install(tmpdir_factory, common_wheels):
    return _common_wheel_editable_install(tmpdir_factory,
                                          common_wheels,
                                          'setuptools')


@pytest.fixture(scope='session')
def wheel_install(tmpdir_factory, common_wheels):
    return _common_wheel_editable_install(tmpdir_factory,
                                          common_wheels,
                                          'wheel')


def install_egg_link(venv, project_name, egg_info_dir):
    with open(venv.site / 'easy-install.pth', 'a') as fp:
        fp.write(str(egg_info_dir.resolve()) + '\n')
    with open(venv.site / (project_name + '.egg-link'), 'w') as fp:
        fp.write(str(egg_info_dir) + '\n.')


@pytest.fixture(scope='session')
def virtualenv_template(request, tmpdir_factory, pip_src,
                        setuptools_install, common_wheels):

    if six.PY3 and request.config.getoption('--use-venv'):
        venv_type = 'venv'
    else:
        venv_type = 'virtualenv'

    # Create the virtual environment
    tmpdir = Path(str(tmpdir_factory.mktemp('virtualenv')))
    venv = VirtualEnvironment(
        tmpdir.joinpath("venv_orig"), venv_type=venv_type
    )

    # Install setuptools and pip.
    install_egg_link(venv, 'setuptools', setuptools_install)
    pip_editable = Path(str(tmpdir_factory.mktemp('pip'))) / 'pip'
    shutil.copytree(pip_src, pip_editable, symlinks=True)
    # noxfile.py is Python 3 only
    assert compileall.compile_dir(
        str(pip_editable), quiet=1, rx=re.compile("noxfile.py$"),
    )
    subprocess.check_call([venv.bin / 'python', 'setup.py', '-q', 'develop'],
                          cwd=pip_editable)

    # Drop (non-relocatable) launchers.
    for exe in os.listdir(venv.bin):
        if not (
            exe.startswith('python') or
            exe.startswith('libpy')  # Don't remove libpypy-c.so...
        ):
            (venv.bin / exe).unlink()

    # Enable user site packages.
    venv.user_site_packages = True

    # Rename original virtualenv directory to make sure
    # it's not reused by mistake from one of the copies.
    venv_template = tmpdir / "venv_template"
    venv.move(venv_template)
    yield venv


@pytest.fixture(scope="session")
def virtualenv_factory(virtualenv_template):
    def factory(tmpdir):
        return VirtualEnvironment(tmpdir, virtualenv_template)

    return factory


@pytest.fixture
def virtualenv(virtualenv_factory, tmpdir):
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    yield virtualenv_factory(tmpdir.joinpath("workspace", "venv"))


@pytest.fixture
def with_wheel(virtualenv, wheel_install):
    install_egg_link(virtualenv, 'wheel', wheel_install)


@pytest.fixture(scope="session")
def script_factory(virtualenv_factory, deprecated_python):
    def factory(tmpdir, virtualenv=None):
        if virtualenv is None:
            virtualenv = virtualenv_factory(tmpdir.joinpath("venv"))
        return PipTestEnvironment(
            # The base location for our test environment
            tmpdir,

            # Tell the Test Environment where our virtualenv is located
            virtualenv=virtualenv,

            # Do not ignore hidden files, they need to be checked as well
            ignore_hidden=False,

            # We are starting with an already empty directory
            start_clear=False,

            # We want to ensure no temporary files are left behind, so the
            # PipTestEnvironment needs to capture and assert against temp
            capture_temp=True,
            assert_no_temp=True,

            # Deprecated python versions produce an extra deprecation warning
            pip_expect_warning=deprecated_python,
        )

    return factory


@pytest.fixture
def script(tmpdir, virtualenv, script_factory):
    """
    Return a PipTestEnvironment which is unique to each test function and
    will execute all commands inside of the unique virtual environment for this
    test function. The returned object is a
    ``tests.lib.scripttest.PipTestEnvironment``.
    """
    return script_factory(tmpdir.joinpath("workspace"), virtualenv)


@pytest.fixture(scope="session")
def common_wheels():
    """Provide a directory with latest setuptools and wheel wheels"""
    return DATA_DIR.joinpath('common_wheels')


@pytest.fixture(scope="session")
def shared_data(tmpdir_factory):
    return TestData.copy(Path(str(tmpdir_factory.mktemp("data"))))


@pytest.fixture
def data(tmpdir):
    return TestData.copy(tmpdir.joinpath("data"))


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
            returncode = pip_entry_point(list(args))
        except SystemExit as e:
            returncode = e.code or 0
        finally:
            sys.stdout = orig_stdout
        return InMemoryPipResult(returncode, stdout.getvalue())


@pytest.fixture
def in_memory_pip():
    return InMemoryPip()


@pytest.fixture(scope="session")
def deprecated_python():
    """Used to indicate whether pip deprecated this python version"""
    return sys.version_info[:2] in [(2, 7)]


@pytest.fixture(scope="session")
def cert_factory(tmpdir_factory):
    def factory():
        # type: () -> str
        """Returns path to cert/key file.
        """
        output_path = Path(str(tmpdir_factory.mktemp("certs"))) / "cert.pem"
        # Must be Text on PY2.
        cert, key = make_tls_cert(u"localhost")
        with open(str(output_path), "wb") as f:
            f.write(serialize_cert(cert))
            f.write(serialize_key(key))

        return str(output_path)

    return factory


class MockServer(object):
    def __init__(self, server):
        # type: (_MockServer) -> None
        self._server = server
        self._running = False
        self.context = ExitStack()

    @property
    def port(self):
        return self._server.port

    @property
    def host(self):
        return self._server.host

    def set_responses(self, responses):
        # type: (Iterable[Responder]) -> None
        assert not self._running, "responses cannot be set on running server"
        self._server.mock.side_effect = responses

    def start(self):
        # type: () -> None
        assert not self._running, "running server cannot be started"
        self.context.enter_context(server_running(self._server))
        self.context.enter_context(self._set_running())

    @contextmanager
    def _set_running(self):
        self._running = True
        try:
            yield
        finally:
            self._running = False

    def stop(self):
        # type: () -> None
        assert self._running, "idle server cannot be stopped"
        self.context.close()

    def get_requests(self):
        # type: () -> Dict[str, str]
        """Get environ for each received request.
        """
        assert not self._running, "cannot get mock from running server"
        return [
            call.args[0] for call in self._server.mock.call_args_list
        ]


@pytest.fixture
def mock_server():
    server = make_mock_server()
    test_server = MockServer(server)
    with test_server.context:
        yield test_server
