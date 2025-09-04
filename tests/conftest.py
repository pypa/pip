from __future__ import annotations

import abc
import compileall
import contextlib
import fnmatch
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    BinaryIO,
    Callable,
    ClassVar,
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
from pip._internal.locations import _USE_SYSCONFIG
from pip._internal.utils.temp_dir import global_tempdir_manager

from tests.lib import (
    DATA_DIR,
    SRC_DIR,
    CertFactory,
    InMemoryPip,
    PipTestEnvironment,
    ScriptFactory,
    TestData,
    create_basic_wheel_for_package,
)
from tests.lib.server import MockServer, make_mock_server
from tests.lib.venv import VirtualEnvironment, VirtualEnvironmentType

if TYPE_CHECKING:
    from typing_extensions import Self


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
        default="resolvelib",
        choices=["resolvelib", "legacy"],
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


def pytest_collection_modifyitems(config: Config, items: list[pytest.Function]) -> None:
    for item in items:
        if not hasattr(item, "module"):  # e.g.: DoctestTextfile
            continue

        if item.get_closest_marker("search") and not config.getoption("--run-search"):
            item.add_marker(pytest.mark.skip("pip search test skipped"))

        # Exempt tests known to use the network from pytest-subket.
        if item.get_closest_marker("network") is not None:
            item.add_marker(pytest.mark.enable_socket)

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
        if module_root_dir.startswith(("functional", "integration", "lib")):
            item.add_marker(pytest.mark.integration)
        elif module_root_dir.startswith("unit"):
            item.add_marker(pytest.mark.unit)

            # We don't want to allow using the script resource if this is a
            # unit test, as unit tests should not need all that heavy lifting
            if "script" in item.fixturenames:
                raise RuntimeError(
                    "Cannot use the ``script`` funcarg in a unit test: "
                    f"(filename = {module_path}, item = {item})"
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


@pytest.fixture
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

    # Make sure color control variables don't affect internal output.
    monkeypatch.delenv("FORCE_COLOR", False)
    monkeypatch.delenv("NO_COLOR", False)

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
        ctx: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext
    else:
        ctx = global_tempdir_manager

    with ctx():
        yield


@pytest.fixture(scope="session")
def pip_src(tmpdir_factory: pytest.TempPathFactory) -> Path:
    def not_code_files_and_folders(path: str, names: list[str]) -> Iterable[str]:
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


@pytest.fixture(scope="session")
def pip_editable_parts(
    pip_src: Path, tmpdir_factory: pytest.TempPathFactory
) -> tuple[Path, ...]:
    pip_editable = tmpdir_factory.mktemp("pip") / "pip"
    shutil.copytree(pip_src, pip_editable, symlinks=True)
    # noxfile.py is Python 3 only
    assert compileall.compile_dir(
        pip_editable,
        quiet=1,
        rx=re.compile("noxfile.py$"),
    )
    pip_self_install_path = tmpdir_factory.mktemp("pip_self_install")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--target",
            pip_self_install_path,
            "-e",
            pip_editable,
        ]
    )
    pth = next(pip_self_install_path.glob("*pip*.pth"))
    dist_info = next(pip_self_install_path.glob("*.dist-info"))
    return (pth, dist_info)


def _common_wheel_editable_install(
    tmpdir_factory: pytest.TempPathFactory, common_wheels: Path, package: str
) -> Path:
    wheel_candidates = list(common_wheels.glob(f"{package}-*.whl"))
    assert len(wheel_candidates) == 1, (
        f"Missing wheels in {common_wheels}, expected 1 got '{wheel_candidates}'."
        " Are you running the tests via nox? See https://pip.pypa.io/en/latest/development/getting-started/#running-tests"
    )
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


@pytest.fixture(scope="session")
def socket_install(tmpdir_factory: pytest.TempPathFactory, common_wheels: Path) -> Path:
    lib_dir = _common_wheel_editable_install(
        tmpdir_factory, common_wheels, "pytest_subket"
    )
    # pytest-subket is only included so it can intercept and block unexpected
    # network requests. It should NOT be visible to the pip under test.
    dist_info = next(lib_dir.glob("*.dist-info"))
    shutil.rmtree(dist_info)
    return lib_dir


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
    pip_editable_parts: tuple[Path, ...],
    setuptools_install: Path,
    wheel_install: Path,
    coverage_install: Path,
    socket_install: Path,
) -> VirtualEnvironment:
    venv_type: VirtualEnvironmentType
    if request.config.getoption("--use-venv"):
        venv_type = "venv"
    else:
        venv_type = "virtualenv"

    # Create the virtual environment
    tmpdir = tmpdir_factory.mktemp("virtualenv")
    venv = VirtualEnvironment(tmpdir.joinpath("venv_orig"), venv_type=venv_type)

    # Install setuptools, wheel, pytest-subket, and pip.
    install_pth_link(venv, "setuptools", setuptools_install)
    install_pth_link(venv, "wheel", wheel_install)
    install_pth_link(venv, "pytest_subket", socket_install)
    # Also copy pytest-subket's .pth file so it can intercept socket calls.
    with open(venv.site / "pytest_socket.pth", "w") as f:
        f.write(socket_install.joinpath("pytest_socket.pth").read_text())

    pth, dist_info = pip_editable_parts

    shutil.copy(pth, venv.site)
    shutil.copytree(
        dist_info, venv.site / dist_info.name, dirs_exist_ok=True, symlinks=True
    )
    # Create placeholder ``easy-install.pth``, as several tests depend on its
    # existence.  TODO: Ensure ``tests.lib.TestPipResult.files_updated`` correctly
    # detects changed files.
    venv.site.joinpath("easy-install.pth").touch()

    # Install coverage and pth file for executing it in any spawned processes
    # in this virtual environment.
    install_pth_link(venv, "coverage", coverage_install)
    # zz prefix ensures the file is after easy-install.pth.
    with open(venv.site / "zz-coverage-helper.pth", "a") as f:
        f.write("import coverage; coverage.process_startup()")

    # Drop (non-relocatable) launchers.
    for exe in os.listdir(venv.bin):
        if not exe.startswith(("python", "libpy")):  # Don't remove libpypy-c.so...
            (venv.bin / exe).unlink()

    # Rename original virtualenv directory to make sure
    # it's not reused by mistake from one of the copies.
    venv_template = tmpdir / "venv_template"
    venv.move(venv_template)
    return venv


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
) -> VirtualEnvironment:
    """
    Return a virtual environment which is unique to each test function
    invocation created inside of a sub directory of the test function's
    temporary directory. The returned object is a
    ``tests.lib.venv.VirtualEnvironment`` object.
    """
    return virtualenv_factory(tmpdir.joinpath("workspace", "venv"))


@pytest.fixture(scope="session")
def script_factory(
    virtualenv_factory: Callable[[Path], VirtualEnvironment],
    deprecated_python: bool,
    zipapp: str | None,
) -> ScriptFactory:
    def factory(
        tmpdir: Path,
        virtualenv: VirtualEnvironment | None = None,
        environ: dict[AnyStr, AnyStr] | None = None,
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
) -> str | None:
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
def session_script(
    request: pytest.FixtureRequest,
    tmpdir_factory: pytest.TempPathFactory,
    virtualenv_factory: Callable[[Path], VirtualEnvironment],
    script_factory: ScriptFactory,
) -> PipTestEnvironment:
    """PipTestEnvironment shared across the whole session.

    This is used by session-scoped fixtures. Tests should use the
    function-scoped ``script`` fixture instead.
    """
    virtualenv = virtualenv_factory(
        tmpdir_factory.mktemp("session_venv").joinpath("venv")
    )
    return script_factory(tmpdir_factory.mktemp("session_workspace"), virtualenv)


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


@pytest.fixture
def in_memory_pip() -> InMemoryPip:
    return InMemoryPip()


@pytest.fixture(scope="session")
def deprecated_python() -> bool:
    """Used to indicate whether pip deprecated this Python version"""
    return sys.version_info[:2] in []


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
class FakePackageSource:
    """A test package file which may be hardcoded or generated dynamically."""

    source_file: str | Path

    @classmethod
    def shared_data_package(cls, name: str) -> FakePackageSource:
        return cls(source_file=name)

    @property
    def _is_shared_data(self) -> bool:
        return isinstance(self.source_file, str)

    @classmethod
    def generated_wheel(cls, path: Path) -> FakePackageSource:
        return cls(source_file=path)

    @property
    def filename(self) -> str:
        if self._is_shared_data:
            assert isinstance(self.source_file, str)
            return self.source_file
        assert isinstance(self.source_file, Path)
        return self.source_file.name

    def source_path(self, shared_data: TestData) -> Path:
        if self._is_shared_data:
            return shared_data.packages / self.filename
        assert isinstance(self.source_file, Path)
        return self.source_file


@dataclass(frozen=True)
class FakePackage:
    """Mock package structure used to generate a PyPI repository.

    FakePackage name and version should correspond to sdists (.tar.gz files) in our test
    data."""

    name: str
    version: str
    source_file: FakePackageSource
    metadata: MetadataKind
    # This will override any dependencies specified in the actual dist's METADATA.
    requires_dist: tuple[str, ...] = ()
    # This will override the Name specified in the actual dist's METADATA.
    metadata_name: str | None = None

    @property
    def filename(self) -> str:
        return self.source_file.filename

    def source_path(self, shared_data: TestData) -> Path:
        return self.source_file.source_path(shared_data)

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
def fake_packages(session_script: PipTestEnvironment) -> dict[str, list[FakePackage]]:
    """The package database we generate for testing PEP 658 support."""
    large_compilewheel_metadata_first = create_basic_wheel_for_package(
        session_script,
        "compilewheel",
        "2.0",
        extra_files={"asdf.txt": b"a" * 10_000},
        # Several tensorflow-gpu uploads place the .dist-info at the beginning of the
        # wheel, which may be a relic of the way bazel generates wheels.
        metadata_first=True,
    )
    # This wheel must be larger than 10KB to trigger the lazy wheel behavior we want
    # to test.
    assert large_compilewheel_metadata_first.stat().st_size > 10_000

    large_translationstring_metadata_last = create_basic_wheel_for_package(
        session_script,
        "translationstring",
        "0.1",
        extra_files={"asdf.txt": b"a" * 10_000},
        metadata_first=False,
    )
    assert large_translationstring_metadata_last.stat().st_size > 10_000

    return {
        "simple": [
            FakePackage(
                "simple",
                "1.0",
                FakePackageSource.shared_data_package("simple-1.0.tar.gz"),
                MetadataKind.Sha256,
            ),
            FakePackage(
                "simple",
                "2.0",
                FakePackageSource.shared_data_package("simple-2.0.tar.gz"),
                MetadataKind.No,
            ),
            # This will raise a hashing error.
            FakePackage(
                "simple",
                "3.0",
                FakePackageSource.shared_data_package("simple-3.0.tar.gz"),
                MetadataKind.WrongHash,
            ),
        ],
        "simple2": [
            # Override the dependencies here in order to force pip to download
            # simple-1.0.tar.gz as well.
            FakePackage(
                "simple2",
                "1.0",
                FakePackageSource.shared_data_package("simple2-1.0.tar.gz"),
                MetadataKind.Unhashed,
                ("simple==1.0",),
            ),
            # This will raise an error when pip attempts to fetch the metadata file.
            FakePackage(
                "simple2",
                "2.0",
                FakePackageSource.shared_data_package("simple2-2.0.tar.gz"),
                MetadataKind.NoFile,
            ),
            # This has a METADATA file with a mismatched name.
            FakePackage(
                "simple2",
                "3.0",
                FakePackageSource.shared_data_package("simple2-3.0.tar.gz"),
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
                FakePackageSource.shared_data_package(
                    "colander-0.9.9-py2.py3-none-any.whl"
                ),
                MetadataKind.No,
            ),
        ],
        "compilewheel": [
            # Ensure we can override the dependencies of a wheel file by injecting PEP
            # 658 metadata.
            FakePackage(
                "compilewheel",
                "1.0",
                FakePackageSource.shared_data_package(
                    "compilewheel-1.0-py2.py3-none-any.whl"
                ),
                MetadataKind.Unhashed,
                ("simple==1.0",),
            ),
            # This inserts a wheel larger than the default fast-deps request size with
            # .dist-info metadata at the front.
            FakePackage(
                "compilewheel",
                "2.0",
                FakePackageSource.generated_wheel(large_compilewheel_metadata_first),
                MetadataKind.No,
            ),
        ],
        "has-script": [
            # Ensure we check PEP 658 metadata hashing errors for wheel files.
            FakePackage(
                "has-script",
                "1.0",
                FakePackageSource.shared_data_package(
                    "has.script-1.0-py2.py3-none-any.whl"
                ),
                MetadataKind.WrongHash,
            ),
        ],
        "translationstring": [
            # This inserts a wheel larger than the default fast-deps request size with
            # .dist-info metadata at the back.
            FakePackage(
                "translationstring",
                "0.1",
                FakePackageSource.generated_wheel(
                    large_translationstring_metadata_last
                ),
                MetadataKind.No,
            ),
            FakePackage(
                "translationstring",
                "1.1",
                FakePackageSource.shared_data_package("translationstring-1.1.tar.gz"),
                MetadataKind.No,
            ),
        ],
        "priority": [
            # Ensure we check for a missing metadata file for wheels.
            FakePackage(
                "priority",
                "1.0",
                FakePackageSource.shared_data_package(
                    "priority-1.0-py2.py3-none-any.whl"
                ),
                MetadataKind.NoFile,
            ),
        ],
        "requires-simple-extra": [
            # Metadata name is not canonicalized.
            FakePackage(
                "requires-simple-extra",
                "0.1",
                FakePackageSource.shared_data_package(
                    "requires_simple_extra-0.1-py2.py3-none-any.whl"
                ),
                MetadataKind.Sha256,
                metadata_name="Requires_Simple.Extra",
            ),
        ],
    }


@pytest.fixture(scope="session")
def html_index_for_packages(
    shared_data: TestData,
    fake_packages: dict[str, list[FakePackage]],
    tmpdir_factory: pytest.TempPathFactory,
) -> Path:
    """Generate a PyPI HTML package index within a local directory pointing to
    synthetic test data."""
    html_dir = tmpdir_factory.mktemp("fake_index_html_content")

    # (1) Generate the content for a PyPI index.html.
    pkg_links = "\n".join(
        f'    <a href="{pkg}/index.html">{pkg}</a>' for pkg in fake_packages.keys()
    )
    # Output won't be nicely indented because dedent() acts after f-string
    # arg insertion.
    index_html = dedent(
        f"""\
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
    )
    # (2) Generate the index.html in a new subdirectory of the temp directory.
    (html_dir / "index.html").write_text(index_html)

    # (3) Generate subdirectories for individual packages, each with their own
    # index.html.
    for pkg, links in fake_packages.items():
        pkg_subdir = html_dir / pkg
        pkg_subdir.mkdir()

        download_links: list[str] = []
        for package_link in links:
            # (3.1) Generate the <a> tag which pip can crawl pointing to this
            # specific package version.
            download_links.append(
                f'    <a href="{package_link.filename}" {package_link.generate_additional_tag()}>{package_link.filename}</a><br/>'  # noqa: E501
            )
            # (3.2) Copy over the corresponding file in `shared_data.packages`, or the
            #       generated wheel path if provided.
            source_path = package_link.source_path(shared_data)
            shutil.copy(
                source_path,
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
        pkg_index_content = dedent(
            f"""\
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
        )
        with open(pkg_subdir / "index.html", "w") as f:
            f.write(pkg_index_content)

    return html_dir


class OneTimeDownloadHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from the current directory, but error if a file is downloaded more
    than once."""

    # NB: Needs to be set on per-function subclass.
    _seen_paths: ClassVar[set[str]] = set()

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


@pytest.fixture
def html_index_with_onetime_server(
    html_index_for_packages: Path,
) -> Iterator[http.server.ThreadingHTTPServer]:
    """Serve files from a generated pypi index, erroring if a file is downloaded more
    than once.

    Provide `-i http://localhost:<port>` to pip invocations to point them at
    this server.
    """

    class InDirectoryServer(http.server.ThreadingHTTPServer):
        def finish_request(self: Self, request: Any, client_address: Any) -> None:
            self.RequestHandlerClass(
                request,
                client_address,
                self,
                directory=str(html_index_for_packages),  # type: ignore[call-arg]
            )

    class Handler(OneTimeDownloadHandler):
        _seen_paths: ClassVar[set[str]] = set()

    with InDirectoryServer(("", 0), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.start()

        try:
            yield httpd
        finally:
            httpd.shutdown()
            server_thread.join()


class RangeHandler(Enum):
    """All the modes of handling range requests we want pip to handle."""

    Always200OK = "always-200-ok"
    NoNegativeRange = "no-negative-range"
    SneakilyCoerceNegativeRange = "sneakily-coerce-negative-range"
    SupportsNegativeRange = "supports-negative-range"
    NegativeRangeOverflowing = "negative-range-overflowing"

    def supports_range(self) -> bool:
        return self in [
            type(self).NoNegativeRange,
            type(self).SneakilyCoerceNegativeRange,
            type(self).SupportsNegativeRange,
            type(self).NegativeRangeOverflowing,
        ]

    def supports_negative_range(self) -> bool:
        return self in [
            type(self).SupportsNegativeRange,
            type(self).NegativeRangeOverflowing,
        ]

    def sneakily_coerces_negative_range(self) -> bool:
        return self == type(self).SneakilyCoerceNegativeRange

    def overflows_negative_range(self) -> bool:
        return self == type(self).NegativeRangeOverflowing


class ContentRangeDownloadHandler(
    http.server.SimpleHTTPRequestHandler, metaclass=abc.ABCMeta
):
    """Extend the basic ``http.server`` to support content ranges."""

    @abc.abstractproperty
    def range_handler(self) -> RangeHandler: ...

    # NB: Needs to be set on per-function subclasses.
    get_request_counts: ClassVar[dict[str, int]] = {}
    positive_range_request_paths: ClassVar[set[str]] = set()
    negative_range_request_paths: ClassVar[set[str]] = set()
    head_request_paths: ClassVar[set[str]] = set()
    ok_response_counts: ClassVar[dict[str, int]] = {}

    @contextmanager
    def _translate_path(self) -> Iterator[tuple[BinaryIO, str, int] | None]:
        # Only test fast-deps, not PEP 658.
        if self.path.endswith(".metadata"):
            self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")
            yield None
            return

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")

        ctype = self.guess_type(path)
        try:
            with open(path, "rb") as f:
                fs = os.fstat(f.fileno())
                full_file_length = fs[6]

                yield (f, ctype, full_file_length)
        except OSError:
            self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")
            yield None
            return

    def _send_basic_headers(self, ctype: str) -> None:
        self.send_header("Content-Type", ctype)
        if self.range_handler.supports_range():
            self.send_header("Accept-Ranges", "bytes")
        # NB: callers must call self.end_headers()!

    def _send_full_file_headers(self, ctype: str, full_file_length: int) -> None:
        self.send_response(http.HTTPStatus.OK)
        self.ok_response_counts.setdefault(self.path, 0)
        self.ok_response_counts[self.path] += 1
        self._send_basic_headers(ctype)
        self.send_header("Content-Length", str(full_file_length))
        self.end_headers()

    def do_HEAD(self) -> None:
        self.head_request_paths.add(self.path)

        with self._translate_path() as x:
            if x is None:
                return
            (_, ctype, full_file_length) = x
            self._send_full_file_headers(ctype, full_file_length)

    def do_GET(self) -> None:
        self.get_request_counts.setdefault(self.path, 0)
        self.get_request_counts[self.path] += 1

        with self._translate_path() as x:
            if x is None:
                return
            (f, ctype, full_file_length) = x
            range_arg = self.headers.get("Range", None)
            if range_arg is not None:
                m = re.match(r"bytes=([0-9]+)?-([0-9]+)", range_arg)
                if m is not None:
                    if m.group(1) is None:
                        self.negative_range_request_paths.add(self.path)
                    else:
                        self.positive_range_request_paths.add(self.path)
            # If no range given, return the whole file.
            if range_arg is None or not self.range_handler.supports_range():
                self._send_full_file_headers(ctype, full_file_length)
                self.copyfile(f, self.wfile)
                return
            # Otherwise, return the requested contents.
            assert m is not None
            # This is a "start-end" range.
            if m.group(1) is not None:
                start = int(m.group(1))
                end = int(m.group(2))
                assert start <= end
                was_out_of_bounds = (end + 1) > full_file_length
            else:
                # This is a "-end" range.
                if self.range_handler.sneakily_coerces_negative_range():
                    end = int(m.group(2))
                    self.send_response(http.HTTPStatus.PARTIAL_CONTENT)
                    self._send_basic_headers(ctype)
                    self.send_header("Content-Length", str(end + 1))
                    self.send_header(
                        "Content-Range", f"bytes 0-{end}/{full_file_length}"
                    )
                    self.end_headers()
                    f.seek(0)
                    self.wfile.write(f.read(end + 1))
                    return
                if not self.range_handler.supports_negative_range():
                    self.send_response(http.HTTPStatus.NOT_IMPLEMENTED)
                    self._send_basic_headers(ctype)
                    self.end_headers()
                    return
                end = full_file_length - 1
                start = end - int(m.group(2)) + 1
                was_out_of_bounds = start < 0
            if was_out_of_bounds:
                if self.range_handler.overflows_negative_range():
                    self._send_full_file_headers(ctype, full_file_length)
                    self.copyfile(f, self.wfile)
                    return
                self.send_response(http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self._send_basic_headers(ctype)
                self.send_header("Content-Range", f"bytes */{full_file_length}")
                self.end_headers()
                return
            sent_length = end - start + 1
            self.send_response(http.HTTPStatus.PARTIAL_CONTENT)
            self._send_basic_headers(ctype)
            self.send_header("Content-Length", str(sent_length))
            self.send_header("Content-Range", f"bytes {start}-{end}/{full_file_length}")
            self.end_headers()
            f.seek(start)
            self.wfile.write(f.read(sent_length))


@pytest.fixture(scope="session")
def html_index_no_metadata(
    html_index_for_packages: Path,
    tmpdir_factory: pytest.TempPathFactory,
) -> Path:
    """Return an index like ``html_index_for_packages`` without any PEP 658 metadata.

    While we already return a 404 in ``ContentRangeDownloadHandler`` for ``.metadata``
    paths, we need to also remove ``data-dist-info-metadata`` attrs on ``<a>`` tags,
    otherwise pip will error after attempting to retrieve the metadata files."""
    new_html_dir = tmpdir_factory.mktemp("fake_index_html_content_no_metadata")
    new_html_dir.rmdir()
    shutil.copytree(html_index_for_packages, new_html_dir)
    for index_page in new_html_dir.rglob("index.html"):
        prev_index = index_page.read_text()
        no_metadata_index = re.sub(r'data-dist-info-metadata="[^"]+"', "", prev_index)
        index_page.write_text(no_metadata_index)
    return new_html_dir


HTMLIndexWithRangeServer = Callable[
    [RangeHandler],
    "AbstractContextManager[tuple[type[ContentRangeDownloadHandler], int]]",
]


@pytest.fixture
def html_index_with_range_server(
    html_index_no_metadata: Path,
) -> HTMLIndexWithRangeServer:
    """Serve files from a generated pypi index, with support for range requests.

    Provide `-i http://localhost:<port>` to pip invocations to point them at
    this server.
    """

    class InDirectoryServer(http.server.ThreadingHTTPServer):
        def finish_request(self, request: Any, client_address: Any) -> None:
            self.RequestHandlerClass(
                request, client_address, self, directory=str(html_index_no_metadata)  # type: ignore[call-arg,arg-type]
            )

    @contextmanager
    def inner(
        range_handler: RangeHandler,
    ) -> Iterator[tuple[type[ContentRangeDownloadHandler], int]]:
        class Handler(ContentRangeDownloadHandler):
            @property
            def range_handler(self) -> RangeHandler:
                return range_handler

            get_request_counts: ClassVar[dict[str, int]] = {}
            positive_range_request_paths: ClassVar[set[str]] = set()
            negative_range_request_paths: ClassVar[set[str]] = set()
            head_request_paths: ClassVar[set[str]] = set()
            ok_response_counts: ClassVar[dict[str, int]] = {}

        with InDirectoryServer(("", 0), Handler) as httpd:
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.start()

            server_port = httpd.server_address[1]
            try:
                yield (Handler, server_port)
            finally:
                httpd.shutdown()
                server_thread.join()

    return inner
