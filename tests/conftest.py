import compileall
import fnmatch
import http.server
import io
import os
import re
import shutil
import subprocess
import sys
import threading
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from unittest.mock import patch
from zipfile import ZipFile

import pytest

# Config will be available from the public API in pytest >= 7.0.0:
# https://github.com/pytest-dev/pytest/commit/88d84a57916b592b070f4201dc84f0286d1f9fef
from _pytest.config import Config

# Parser will be available from the public API in pytest >= 7.0.0:
# https://github.com/pytest-dev/pytest/commit/538b5c24999e9ebb4fab43faabc8bcc28737bcdf
from _pytest.config.argparsing import Parser
from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile

from pip import __file__ as pip_location
from pip._internal.cli.main import main as pip_entry_point
from pip._internal.locations import _USE_SYSCONFIG
from pip._internal.utils.temp_dir import global_tempdir_manager
from tests.lib import DATA_DIR, SRC_DIR, PipTestEnvironment, TestData
from tests.lib.server import MockServer as _MockServer
from tests.lib.server import make_mock_server, server_running
from tests.lib.venv import VirtualEnvironment, VirtualEnvironmentType

from .lib.compat import nullcontext

if TYPE_CHECKING:
    from typing import Protocol

    from _typeshed.wsgi import WSGIApplication
else:
    # TODO: Protocol was introduced in Python 3.8. Remove this branch when
    # dropping support for Python 3.7.
    Protocol = object


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--keep-tmpdir",
        action="store_true",
        default=False,
        help="keep temporary test directories",
    )
    parser.addoption(
        "--resolver",
        action="store",
        default="2020-resolver",
        choices=["2020-resolver", "legacy"],
        help="use given resolver in tests",
    )
    parser.addoption(
        "--use-venv",
        action="store_true",
        default=False,
        help="use venv for virtual environment creation",
    )
    parser.addoption(
        "--run-search",
        action="store_true",
        default=False,
        help="run 'pip search' tests",
    )
    parser.addoption(
        "--proxy",
        action="store",
        default=None,
        help="use given proxy in session network tests",
    )
    parser.addoption(
        "--use-zipapp",
        action="store_true",
        default=False,
        help="use a zipapp when running pip in tests",
    )


def pytest_collection_modifyitems(config: Config, items: List[pytest.Function]) -> None:
    for item in items:
        if not hasattr(item, "module"):  # e.g.: DoctestTextfile
            continue

        if item.get_closest_marker("search") and not config.getoption("--run-search"):
            item.add_marker(pytest.mark.skip("pip search test skipped"))

        if "CI" in os.environ:
            # Mark network tests as flaky
            if item.get_closest_marker("network") is not None:
                item.add_marker(pytest.mark.flaky(reruns=3, reruns_delay=2))

        if (
            item.get_closest_marker("incompatible_with_venv")
            and sys.prefix != sys.base_prefix
        ):
            item.add_marker(pytest.mark.skip("Incompatible with venv"))

        if item.get_closest_marker("incompatible_with_sysconfig") and _USE_SYSCONFIG:
            item.add_marker(pytest.mark.skip("Incompatible with sysconfig"))

        module_file = item.module.__file__
        module_path = os.path.relpath(
            module_file, os.path.commonprefix([__file__, module_file])
        )

        module_root_dir = module_path.split(os.pathsep)[0]
        if (
            module_root_dir.startswith("functional")
            or module_root_dir.startswith("integration")
            or module_root_dir.startswith("lib")
        ):
            item.add_marker(pytest.mark.integration)
        elif module_root_dir.startswith("unit"):
            item.add_marker(pytest.mark.unit)

            # We don't want to allow using the script resource if this is a
            # unit test, as unit tests should not need all that heavy lifting
            if "script" in item.fixturenames:
                raise RuntimeError(
                    "Cannot use the ``script`` funcarg in a unit test: "
                    "(filename = {}, item = {})".format(module_path, item)
                )
        else:
            raise RuntimeError(f"Unknown test type (filename = {module_path})")


@pytest.fixture(scope="session", autouse=True)
def resolver_variant(request: pytest.FixtureRequest) -> Iterator[str]:
    """Set environment variable to make pip default to the correct resolver."""
    resolver = request.config.getoption("--resolver")

    # Handle the environment variables for this test.
    features = set(os.environ.get("PIP_USE_FEATURE", "").split())
    deprecated_features = set(os.environ.get("PIP_USE_DEPRECATED", "").split())

    if resolver == "legacy":
        deprecated_features.add("legacy-resolver")
    else:
        deprecated_features.discard("legacy-resolver")

    env = {
        "PIP_USE_FEATURE": " ".join(features),
        "PIP_USE_DEPRECATED": " ".join(deprecated_features),
    }
    with patch.dict(os.environ, env):
        yield resolver


@pytest.fixture(scope="session")
def tmp_path_factory(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[pytest.TempPathFactory]:
    """Modified `tmpdir_factory` session fixture
    that will automatically cleanup after itself.
    """
    yield tmp_path_factory
    if not request.config.getoption("--keep-tmpdir"):
        shutil.rmtree(
            tmp_path_factory.getbasetemp(),
            ignore_errors=True,
        )


@pytest.fixture(scope="session")
def tmpdir_factory(tmp_path_factory: pytest.TempPathFactory) -> pytest.TempPathFactory:
    """Override Pytest's ``tmpdir_factory`` with our pathlib implementation.

    This prevents mis-use of this fixture.
    """
    return tmp_path_factory


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Path]:
    """
    Return a temporary directory path object which is unique to each test
    function invocation, created as a sub directory of the base temporary
    directory. The returned object is a ``Path`` object.

    This uses the built-in tmp_path fixture from pytest itself, but deletes the
    temporary directories at the end of each test case.
    """
    assert tmp_path.is_dir()
    yield tmp_path
    # Clear out the temporary directory after the test has finished using it.
    # This should prevent us from needing a multiple gigabyte temporary
    # directory while running the tests.
    if not request.config.getoption("--keep-tmpdir"):
        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture()
def tmpdir(tmp_path: Path) -> Path:
    """Override Pytest's ``tmpdir`` with our pathlib implementation.

    This prevents mis-use of this fixture.
    """
    return tmp_path


@pytest.fixture(autouse=True)
def isolate(tmpdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    if sys.platform == "win32":
        # Note: this will only take effect in subprocesses...
        home_drive, home_path = os.path.splitdrive(home_dir)
        monkeypatch.setenv("USERPROFILE", home_dir)
        monkeypatch.setenv("HOMEDRIVE", home_drive)
        monkeypatch.setenv("HOMEPATH", home_path)
        for env_var, sub_path in (
            ("APPDATA", "AppData/Roaming"),
            ("LOCALAPPDATA", "AppData/Local"),
        ):
            path = os.path.join(home_dir, *sub_path.split("/"))
            monkeypatch.setenv(env_var, path)
            os.makedirs(path)
    else:
        # Set our home directory to our temporary directory, this should force
        # all of our relative configuration files to be read from here instead
        # of the user's actual $HOME directory.
        monkeypatch.setenv("HOME", home_dir)
        # Isolate ourselves from XDG directories
        monkeypatch.setenv(
            "XDG_DATA_HOME",
            os.path.join(
                home_dir,
                ".local",
                "share",
            ),
        )
        monkeypatch.setenv(
            "XDG_CONFIG_HOME",
            os.path.join(
                home_dir,
                ".config",
            ),
        )
        monkeypatch.setenv("XDG_CACHE_HOME", os.path.join(home_dir, ".cache"))
        monkeypatch.setenv(
            "XDG_RUNTIME_DIR",
            os.path.join(
                home_dir,
                ".runtime",
            ),
        )
        monkeypatch.setenv(
            "XDG_DATA_DIRS",
            os.pathsep.join(
                [
                    os.path.join(fake_root, "usr", "local", "share"),
                    os.path.join(fake_root, "usr", "share"),
                ]
            ),
        )
        monkeypatch.setenv(
            "XDG_CONFIG_DIRS",
            os.path.join(
                fake_root,
                "etc",
                "xdg",
            ),
        )

    # Configure git, because without an author name/email git will complain
    # and cause test failures.
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "pip")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "distutils-sig@python.org")

    # We want to disable the version check from running in the tests
    monkeypatch.setenv("PIP_DISABLE_PIP_VERSION_CHECK", "true")

    # Make sure tests don't share a requirements tracker.
    monkeypatch.delenv("PIP_BUILD_TRACKER", False)

    # FIXME: Windows...
    os.makedirs(os.path.join(home_dir, ".config", "git"))
    with open(os.path.join(home_dir, ".config", "git", "config"), "wb") as fp:
        fp.write(b"[user]\n\tname = pip\n\temail = distutils-sig@python.org\n")


@pytest.fixture(autouse=True)
def scoped_global_tempdir_manager(request: pytest.FixtureRequest) -> Iterator[None]:
    """Make unit tests with globally-managed tempdirs easier

    Each test function gets its own individual scope for globally-managed
    temporary directories in the application.
    """
    if "no_auto_tempdir_manager" in request.keywords:
        ctx = nullcontext
    else:
        ctx = global_tempdir_manager

    with ctx():
        yield


@pytest.fixture(scope="session")
def pip_src(tmpdir_factory: pytest.TempPathFactory) -> Path:
    def not_code_files_and_folders(path: str, names: List[str]) -> Iterable[str]:
        # In the root directory...
        if os.path.samefile(path, SRC_DIR):
            # ignore all folders except "src"
            folders = {
                name for name in names if os.path.isdir(os.path.join(path, name))
            }
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

    pip_src = tmpdir_factory.mktemp("pip_src").joinpath("pip_src")
    # Copy over our source tree so that each use is self contained
    shutil.copytree(
        SRC_DIR,
        pip_src.resolve(),
        ignore=not_code_files_and_folders,
    )
    return pip_src


def _common_wheel_editable_install(
    tmpdir_factory: pytest.TempPathFactory, common_wheels: Path, package: str
) -> Path:
    wheel_candidates = list(common_wheels.glob(f"{package}-*.whl"))
    assert len(wheel_candidates) == 1, wheel_candidates
    install_dir = tmpdir_factory.mktemp(package) / "install"
    lib_install_dir = install_dir / "lib"
    bin_install_dir = install_dir / "bin"
    with WheelFile.open(wheel_candidates[0]) as source:
        install(
            source,
            SchemeDictionaryDestination(
                {
                    "purelib": os.fspath(lib_install_dir),
                    "platlib": os.fspath(lib_install_dir),
                    "scripts": os.fspath(bin_install_dir),
                },
                interpreter=sys.executable,
                script_kind="posix",
            ),
            additional_metadata={},
        )
    # The scripts are not necessary for our use cases, and they would be installed with
    # the wrong interpreter, so remove them.
    # TODO consider a refactoring by adding a install_from_wheel(path) method
    # to the virtualenv fixture.
    if bin_install_dir.exists():
        shutil.rmtree(bin_install_dir)
    return lib_install_dir


@pytest.fixture(scope="session")
def setuptools_install(
    tmpdir_factory: pytest.TempPathFactory, common_wheels: Path
) -> Path:
    return _common_wheel_editable_install(tmpdir_factory, common_wheels, "setuptools")


@pytest.fixture(scope="session")
def wheel_install(tmpdir_factory: pytest.TempPathFactory, common_wheels: Path) -> Path:
    return _common_wheel_editable_install(tmpdir_factory, common_wheels, "wheel")


@pytest.fixture(scope="session")
def coverage_install(
    tmpdir_factory: pytest.TempPathFactory, common_wheels: Path
) -> Path:
    return _common_wheel_editable_install(tmpdir_factory, common_wheels, "coverage")


def install_pth_link(
    venv: VirtualEnvironment, project_name: str, lib_dir: Path
) -> None:
    venv.site.joinpath(f"_pip_testsuite_{project_name}.pth").write_text(
        str(lib_dir.resolve()), encoding="utf-8"
    )


@pytest.fixture(scope="session")
def virtualenv_template(
    request: pytest.FixtureRequest,
    tmpdir_factory: pytest.TempPathFactory,
    pip_src: Path,
    setuptools_install: Path,
    wheel_install: Path,
    coverage_install: Path,
) -> Iterator[VirtualEnvironment]:
    venv_type: VirtualEnvironmentType
    if request.config.getoption("--use-venv"):
        venv_type = "venv"
    else:
        venv_type = "virtualenv"

    # Create the virtual environment
    tmpdir = tmpdir_factory.mktemp("virtualenv")
    venv = VirtualEnvironment(tmpdir.joinpath("venv_orig"), venv_type=venv_type)

    # Install setuptools, wheel and pip.
    install_pth_link(venv, "setuptools", setuptools_install)
    install_pth_link(venv, "wheel", wheel_install)
    pip_editable = tmpdir_factory.mktemp("pip") / "pip"
    shutil.copytree(pip_src, pip_editable, symlinks=True)
    # noxfile.py is Python 3 only
    assert compileall.compile_dir(
        str(pip_editable),
        quiet=1,
        rx=re.compile("noxfile.py$"),
    )
    subprocess.check_call(
        [os.fspath(venv.bin / "python"), "setup.py", "-q", "develop"], cwd=pip_editable
    )

    # Install coverage and pth file for executing it in any spawned processes
    # in this virtual environment.
    install_pth_link(venv, "coverage", coverage_install)
    # zz prefix ensures the file is after easy-install.pth.
    with open(venv.site / "zz-coverage-helper.pth", "a") as f:
        f.write("import coverage; coverage.process_startup()")

    # Drop (non-relocatable) launchers.
    for exe in os.listdir(venv.bin):
        if not (
            exe.startswith("python")
            or exe.startswith("libpy")  # Don't remove libpypy-c.so...
        ):
            (venv.bin / exe).unlink()

    # Rename original virtualenv directory to make sure
    # it's not reused by mistake from one of the copies.
    venv_template = tmpdir / "venv_template"
    venv.move(venv_template)
    yield venv


@pytest.fixture(scope="session")
def virtualenv_factory(
    virtualenv_template: VirtualEnvironment,
) -> Callable[[Path], VirtualEnvironment]:
    def factory(tmpdir: Path) -> VirtualEnvironment:
        return VirtualEnvironment(tmpdir, virtualenv_template)

    return factory


@pytest.fixture
def virtualenv(
    virtualenv_factory: Callable[[Path], VirtualEnvironment], tmpdir: Path
) -> Iterator[VirtualEnvironment]:
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    yield virtualenv_factory(tmpdir.joinpath("workspace", "venv"))


class ScriptFactory(Protocol):
    def __call__(
        self,
        tmpdir: Path,
        virtualenv: Optional[VirtualEnvironment] = None,
        environ: Optional[Dict[AnyStr, AnyStr]] = None,
    ) -> PipTestEnvironment:
        ...


@pytest.fixture(scope="session")
def script_factory(
    virtualenv_factory: Callable[[Path], VirtualEnvironment],
    deprecated_python: bool,
    zipapp: Optional[str],
) -> ScriptFactory:
    def factory(
        tmpdir: Path,
        virtualenv: Optional[VirtualEnvironment] = None,
        environ: Optional[Dict[AnyStr, AnyStr]] = None,
    ) -> PipTestEnvironment:
        kwargs = {}
        if environ:
            kwargs["environ"] = environ
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
            # Tell the Test Environment if we want to run pip via a zipapp
            zipapp=zipapp,
            **kwargs,
        )

    return factory


ZIPAPP_MAIN = """\
#!/usr/bin/env python

import os
import runpy
import sys

lib = os.path.join(os.path.dirname(__file__), "lib")
sys.path.insert(0, lib)

runpy.run_module("pip", run_name="__main__")
"""


def make_zipapp_from_pip(zipapp_name: Path) -> None:
    pip_dir = Path(pip_location).parent
    with zipapp_name.open("wb") as zipapp_file:
        zipapp_file.write(b"#!/usr/bin/env python\n")
        with ZipFile(zipapp_file, "w") as zipapp:
            for pip_file in pip_dir.rglob("*"):
                if pip_file.suffix == ".pyc":
                    continue
                if pip_file.name == "__pycache__":
                    continue
                rel_name = pip_file.relative_to(pip_dir.parent)
                zipapp.write(pip_file, arcname=f"lib/{rel_name}")
            zipapp.writestr("__main__.py", ZIPAPP_MAIN)


@pytest.fixture(scope="session")
def zipapp(
    request: pytest.FixtureRequest, tmpdir_factory: pytest.TempPathFactory
) -> Optional[str]:
    """
    If the user requested for pip to be run from a zipapp, build that zipapp
    and return its location. If the user didn't request a zipapp, return None.

    This fixture is session scoped, so the zipapp will only be created once.
    """
    if not request.config.getoption("--use-zipapp"):
        return None

    temp_location = tmpdir_factory.mktemp("zipapp")
    pyz_file = temp_location / "pip.pyz"
    make_zipapp_from_pip(pyz_file)
    return str(pyz_file)


@pytest.fixture
def script(
    request: pytest.FixtureRequest,
    tmpdir: Path,
    virtualenv: VirtualEnvironment,
    script_factory: ScriptFactory,
) -> PipTestEnvironment:
    """
    Return a PipTestEnvironment which is unique to each test function and
    will execute all commands inside of the unique virtual environment for this
    test function. The returned object is a
    ``tests.lib.PipTestEnvironment``.
    """
    return script_factory(tmpdir.joinpath("workspace"), virtualenv)


@pytest.fixture(scope="session")
def common_wheels() -> Path:
    """Provide a directory with latest setuptools and wheel wheels"""
    return DATA_DIR.joinpath("common_wheels")


@pytest.fixture(scope="session")
def shared_data(tmpdir_factory: pytest.TempPathFactory) -> TestData:
    return TestData.copy(tmpdir_factory.mktemp("data"))


@pytest.fixture
def data(tmpdir: Path) -> TestData:
    return TestData.copy(tmpdir.joinpath("data"))


class InMemoryPipResult:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


class InMemoryPip:
    def pip(self, *args: Union[str, Path]) -> InMemoryPipResult:
        orig_stdout = sys.stdout
        stdout = io.StringIO()
        sys.stdout = stdout
        try:
            returncode = pip_entry_point([os.fspath(a) for a in args])
        except SystemExit as e:
            if isinstance(e.code, int):
                returncode = e.code
            elif e.code:
                returncode = 1
            else:
                returncode = 0
        finally:
            sys.stdout = orig_stdout
        return InMemoryPipResult(returncode, stdout.getvalue())


@pytest.fixture
def in_memory_pip() -> InMemoryPip:
    return InMemoryPip()


@pytest.fixture(scope="session")
def deprecated_python() -> bool:
    """Used to indicate whether pip deprecated this Python version"""
    return sys.version_info[:2] in []


CertFactory = Callable[[], str]


@pytest.fixture(scope="session")
def cert_factory(tmpdir_factory: pytest.TempPathFactory) -> CertFactory:
    # Delay the import requiring cryptography in order to make it possible
    # to deselect relevant tests on systems where cryptography cannot
    # be installed.
    from tests.lib.certs import make_tls_cert, serialize_cert, serialize_key

    def factory() -> str:
        """Returns path to cert/key file."""
        output_path = tmpdir_factory.mktemp("certs") / "cert.pem"
        # Must be Text on PY2.
        cert, key = make_tls_cert("localhost")
        with open(str(output_path), "wb") as f:
            f.write(serialize_cert(cert))
            f.write(serialize_key(key))

        return str(output_path)

    return factory


class MockServer:
    def __init__(self, server: _MockServer) -> None:
        self._server = server
        self._running = False
        self.context = ExitStack()

    @property
    def port(self) -> int:
        return self._server.port

    @property
    def host(self) -> str:
        return self._server.host

    def set_responses(self, responses: Iterable["WSGIApplication"]) -> None:
        assert not self._running, "responses cannot be set on running server"
        self._server.mock.side_effect = responses

    def start(self) -> None:
        assert not self._running, "running server cannot be started"
        self.context.enter_context(server_running(self._server))
        self.context.enter_context(self._set_running())

    @contextmanager
    def _set_running(self) -> Iterator[None]:
        self._running = True
        try:
            yield
        finally:
            self._running = False

    def stop(self) -> None:
        assert self._running, "idle server cannot be stopped"
        self.context.close()

    def get_requests(self) -> List[Dict[str, str]]:
        """Get environ for each received request."""
        assert not self._running, "cannot get mock from running server"
        # Legacy: replace call[0][0] with call.args[0]
        # when pip drops support for python3.7
        return [call[0][0] for call in self._server.mock.call_args_list]


@pytest.fixture
def mock_server() -> Iterator[MockServer]:
    server = make_mock_server()
    test_server = MockServer(server)
    with test_server.context:
        yield test_server


@pytest.fixture
def proxy(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("proxy")


@pytest.fixture
def enable_user_site(virtualenv: VirtualEnvironment) -> None:
    virtualenv.user_site_packages = True


class MetadataKind(Enum):
    """All the types of values we might be provided for the data-dist-info-metadata
    attribute from PEP 658."""

    # Valid: will read metadata from the dist instead.
    No = "none"
    # Valid: will read the .metadata file, but won't check its hash.
    Unhashed = "unhashed"
    # Valid: will read the .metadata file and check its hash matches.
    Sha256 = "sha256"
    # Invalid: will error out after checking the hash.
    WrongHash = "wrong-hash"
    # Invalid: will error out after failing to fetch the .metadata file.
    NoFile = "no-file"


@dataclass(frozen=True)
class FakePackage:
    """Mock package structure used to generate a PyPI repository.

    FakePackage name and version should correspond to sdists (.tar.gz files) in our test
    data."""

    name: str
    version: str
    filename: str
    metadata: MetadataKind
    # This will override any dependencies specified in the actual dist's METADATA.
    requires_dist: Tuple[str, ...] = ()
    # This will override the Name specified in the actual dist's METADATA.
    metadata_name: Optional[str] = None

    def metadata_filename(self) -> str:
        """This is specified by PEP 658."""
        return f"{self.filename}.metadata"

    def generate_additional_tag(self) -> str:
        """This gets injected into the <a> tag in the generated PyPI index page for this
        package."""
        if self.metadata == MetadataKind.No:
            return ""
        if self.metadata in [MetadataKind.Unhashed, MetadataKind.NoFile]:
            return 'data-dist-info-metadata="true"'
        if self.metadata == MetadataKind.WrongHash:
            return 'data-dist-info-metadata="sha256=WRONG-HASH"'
        assert self.metadata == MetadataKind.Sha256
        checksum = sha256(self.generate_metadata()).hexdigest()
        return f'data-dist-info-metadata="sha256={checksum}"'

    def requires_str(self) -> str:
        if not self.requires_dist:
            return ""
        joined = " and ".join(self.requires_dist)
        return f"Requires-Dist: {joined}"

    def generate_metadata(self) -> bytes:
        """This is written to `self.metadata_filename()` and will override the actual
        dist's METADATA, unless `self.metadata == MetadataKind.NoFile`."""
        return dedent(
            f"""\
        Metadata-Version: 2.1
        Name: {self.metadata_name or self.name}
        Version: {self.version}
        {self.requires_str()}
        """
        ).encode("utf-8")


@pytest.fixture(scope="session")
def fake_packages() -> Dict[str, List[FakePackage]]:
    """The package database we generate for testing PEP 658 support."""
    return {
        "simple": [
            FakePackage("simple", "1.0", "simple-1.0.tar.gz", MetadataKind.Sha256),
            FakePackage("simple", "2.0", "simple-2.0.tar.gz", MetadataKind.No),
            # This will raise a hashing error.
            FakePackage("simple", "3.0", "simple-3.0.tar.gz", MetadataKind.WrongHash),
        ],
        "simple2": [
            # Override the dependencies here in order to force pip to download
            # simple-1.0.tar.gz as well.
            FakePackage(
                "simple2",
                "1.0",
                "simple2-1.0.tar.gz",
                MetadataKind.Unhashed,
                ("simple==1.0",),
            ),
            # This will raise an error when pip attempts to fetch the metadata file.
            FakePackage("simple2", "2.0", "simple2-2.0.tar.gz", MetadataKind.NoFile),
            # This has a METADATA file with a mismatched name.
            FakePackage(
                "simple2",
                "3.0",
                "simple2-3.0.tar.gz",
                MetadataKind.Sha256,
                metadata_name="not-simple2",
            ),
        ],
        "colander": [
            # Ensure we can read the dependencies from a metadata file within a wheel
            # *without* PEP 658 metadata.
            FakePackage(
                "colander",
                "0.9.9",
                "colander-0.9.9-py2.py3-none-any.whl",
                MetadataKind.No,
            ),
        ],
        "compilewheel": [
            # Ensure we can override the dependencies of a wheel file by injecting PEP
            # 658 metadata.
            FakePackage(
                "compilewheel",
                "1.0",
                "compilewheel-1.0-py2.py3-none-any.whl",
                MetadataKind.Unhashed,
                ("simple==1.0",),
            ),
        ],
        "has-script": [
            # Ensure we check PEP 658 metadata hashing errors for wheel files.
            FakePackage(
                "has-script",
                "1.0",
                "has.script-1.0-py2.py3-none-any.whl",
                MetadataKind.WrongHash,
            ),
        ],
        "translationstring": [
            FakePackage(
                "translationstring",
                "1.1",
                "translationstring-1.1.tar.gz",
                MetadataKind.No,
            ),
        ],
        "priority": [
            # Ensure we check for a missing metadata file for wheels.
            FakePackage(
                "priority",
                "1.0",
                "priority-1.0-py2.py3-none-any.whl",
                MetadataKind.NoFile,
            ),
        ],
        "requires-simple-extra": [
            # Metadata name is not canonicalized.
            FakePackage(
                "requires-simple-extra",
                "0.1",
                "requires_simple_extra-0.1-py2.py3-none-any.whl",
                MetadataKind.Sha256,
                metadata_name="Requires_Simple.Extra",
            ),
        ],
    }


@pytest.fixture(scope="session")
def html_index_for_packages(
    shared_data: TestData,
    fake_packages: Dict[str, List[FakePackage]],
    tmpdir_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a PyPI HTML package index within a local directory pointing to
    synthetic test data."""
    html_dir = tmpdir_factory.mktemp("fake_index_html_content")

    # (1) Generate the content for a PyPI index.html.
    pkg_links = "\n".join(
        f'    <a href="{pkg}/index.html">{pkg}</a>' for pkg in fake_packages.keys()
    )
    index_html = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Simple index</title>
  </head>
  <body>
{pkg_links}
  </body>
</html>"""
    # (2) Generate the index.html in a new subdirectory of the temp directory.
    (html_dir / "index.html").write_text(index_html)

    # (3) Generate subdirectories for individual packages, each with their own
    # index.html.
    for pkg, links in fake_packages.items():
        pkg_subdir = html_dir / pkg
        pkg_subdir.mkdir()

        download_links: List[str] = []
        for package_link in links:
            # (3.1) Generate the <a> tag which pip can crawl pointing to this
            # specific package version.
            download_links.append(
                f'    <a href="{package_link.filename}" {package_link.generate_additional_tag()}>{package_link.filename}</a><br/>'  # noqa: E501
            )
            # (3.2) Copy over the corresponding file in `shared_data.packages`.
            shutil.copy(
                shared_data.packages / package_link.filename,
                pkg_subdir / package_link.filename,
            )
            # (3.3) Write a metadata file, if applicable.
            if package_link.metadata != MetadataKind.NoFile:
                with open(pkg_subdir / package_link.metadata_filename(), "wb") as f:
                    f.write(package_link.generate_metadata())

        # (3.4) After collating all the download links and copying over the files,
        # write an index.html with the generated download links for each
        # copied file for this specific package name.
        download_links_str = "\n".join(download_links)
        pkg_index_content = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for {pkg}</title>
  </head>
  <body>
    <h1>Links for {pkg}</h1>
{download_links_str}
  </body>
</html>"""
        with open(pkg_subdir / "index.html", "w") as f:
            f.write(pkg_index_content)

    return html_dir


class OneTimeDownloadHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from the current directory, but error if a file is downloaded more
    than once."""

    _seen_paths: ClassVar[Set[str]] = set()

    def do_GET(self) -> None:
        if self.path in self._seen_paths:
            self.send_error(
                http.HTTPStatus.NOT_FOUND,
                f"File {self.path} not available more than once!",
            )
            return
        super().do_GET()
        if not (self.path.endswith("/") or self.path.endswith(".metadata")):
            self._seen_paths.add(self.path)


@pytest.fixture(scope="function")
def html_index_with_onetime_server(
    html_index_for_packages: Path,
) -> Iterator[http.server.ThreadingHTTPServer]:
    """Serve files from a generated pypi index, erroring if a file is downloaded more
    than once.

    Provide `-i http://localhost:8000` to pip invocations to point them at this server.
    """

    class InDirectoryServer(http.server.ThreadingHTTPServer):
        def finish_request(self, request: Any, client_address: Any) -> None:
            self.RequestHandlerClass(
                request, client_address, self, directory=str(html_index_for_packages)  # type: ignore[call-arg] # noqa: E501
            )

    class Handler(OneTimeDownloadHandler):
        _seen_paths: ClassVar[Set[str]] = set()

    with InDirectoryServer(("", 8000), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.start()

        try:
            yield httpd
        finally:
            httpd.shutdown()
            server_thread.join()
