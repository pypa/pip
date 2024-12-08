import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import tomli_w

from pip._internal.build_env import BuildEnvironment
from pip._internal.req import InstallRequirement

from tests.lib import (
    PipTestEnvironment,
    TestData,
    create_basic_wheel_for_package,
    make_test_finder,
)


def make_project(
    tmpdir: Path,
    requires: Optional[List[str]] = None,
    backend: Optional[str] = None,
    backend_path: Optional[List[str]] = None,
) -> Path:
    requires = requires or []
    project_dir = tmpdir / "project"
    project_dir.mkdir()
    buildsys: Dict[str, Any] = {"requires": requires}
    if backend:
        buildsys["build-backend"] = backend
    if backend_path:
        buildsys["backend-path"] = backend_path
    data = tomli_w.dumps({"build-system": buildsys})
    project_dir.joinpath("pyproject.toml").write_text(data)
    return project_dir


def test_backend(tmpdir: Path, data: TestData) -> None:
    """Check we can call a requirement's backend successfully"""
    project_dir = make_project(tmpdir, backend="dummy_backend")
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(project_dir)  # make req believe it has been unpacked
    req.load_pyproject_toml()
    env = BuildEnvironment()
    finder = make_test_finder(find_links=[data.backends])
    env.install_requirements(finder, ["dummy_backend"], "normal", kind="Installing")
    conflicting, missing = env.check_requirements(["dummy_backend"])
    assert not conflicting
    assert not missing
    assert hasattr(req.pep517_backend, "build_wheel")
    with env:
        assert req.pep517_backend is not None
        assert req.pep517_backend.build_wheel("dir") == "Backend called"


dummy_backend_code = """\
def build_wheel(
    wheel_directory,
    config_settings=None,
    metadata_directory=None
):
    return "Backend called"
"""


def test_backend_path(tmpdir: Path, data: TestData) -> None:
    """Check we can call a backend inside the project"""
    project_dir = make_project(tmpdir, backend="dummy_backend", backend_path=["."])
    (project_dir / "dummy_backend.py").write_text(dummy_backend_code)
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(project_dir)  # make req believe it has been unpacked
    req.load_pyproject_toml()

    env = BuildEnvironment()
    assert hasattr(req.pep517_backend, "build_wheel")
    with env:
        assert req.pep517_backend is not None
        assert req.pep517_backend.build_wheel("dir") == "Backend called"


def test_backend_path_and_dep(tmpdir: Path, data: TestData) -> None:
    """Check we can call a requirement's backend successfully"""
    project_dir = make_project(
        tmpdir, backend="dummy_internal_backend", backend_path=["."]
    )
    (project_dir / "dummy_internal_backend.py").write_text(
        "from dummy_backend import build_wheel"
    )
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(project_dir)  # make req believe it has been unpacked
    req.load_pyproject_toml()
    env = BuildEnvironment()
    finder = make_test_finder(find_links=[data.backends])
    env.install_requirements(finder, ["dummy_backend"], "normal", kind="Installing")

    assert hasattr(req.pep517_backend, "build_wheel")
    with env:
        assert req.pep517_backend is not None
        assert req.pep517_backend.build_wheel("dir") == "Backend called"


def test_pep517_install(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    """Check we can build with a custom backend"""
    project_dir = make_project(
        tmpdir, requires=["test_backend"], backend="test_backend"
    )
    result = script.pip("install", "--no-index", "-f", data.backends, project_dir)
    result.assert_installed("project", editable=False)


def test_pep517_install_with_reqs(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    """Backend generated requirements are installed in the build env"""
    project_dir = make_project(
        tmpdir, requires=["test_backend"], backend="test_backend"
    )
    project_dir.joinpath("backend_reqs.txt").write_text("simplewheel")
    result = script.pip(
        "install", "--no-index", "-f", data.backends, "-f", data.packages, project_dir
    )
    result.assert_installed("project", editable=False)


def test_no_use_pep517_without_setup_py(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    """Using --no-use-pep517 requires setup.py"""
    project_dir = make_project(
        tmpdir, requires=["test_backend"], backend="test_backend"
    )
    result = script.pip(
        "install",
        "--no-index",
        "--no-use-pep517",
        "-f",
        data.backends,
        project_dir,
        expect_error=True,
    )
    assert "project does not have a setup.py" in result.stderr


def test_conflicting_pep517_backend_requirements(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    project_dir = make_project(
        tmpdir, requires=["test_backend", "simplewheel==1.0"], backend="test_backend"
    )
    project_dir.joinpath("backend_reqs.txt").write_text("simplewheel==2.0")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.backends,
        "-f",
        data.packages,
        project_dir,
        expect_error=True,
    )
    msg = (
        f"Some build dependencies for {project_dir.as_uri()} conflict with the backend "
        "dependencies: simplewheel==1.0 is incompatible with "
        "simplewheel==2.0."
    )
    assert result.returncode != 0
    assert msg in result.stderr, str(result)


def test_no_check_build_deps(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    project_dir = make_project(
        tmpdir, requires=["simplewheel==2.0"], backend="test_backend"
    )
    script.pip(
        "install",
        "simplewheel==1.0",
        "test_backend",
        "--no-index",
        "-f",
        data.packages,
        "-f",
        data.backends,
    )
    result = script.pip("install", "--no-build-isolation", project_dir)
    result.assert_installed("project", editable=False)


def test_validate_missing_pep517_backend_requirements(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    project_dir = make_project(
        tmpdir, requires=["test_backend", "simplewheel==1.0"], backend="test_backend"
    )
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.backends,
        "-f",
        data.packages,
        "--no-build-isolation",
        "--check-build-dependencies",
        project_dir,
        expect_error=True,
    )
    msg = (
        f"Some build dependencies for {project_dir.as_uri()} are missing: "
        "'simplewheel==1.0', 'test_backend'."
    )
    assert result.returncode != 0
    assert msg in result.stderr, str(result)


def test_validate_conflicting_pep517_backend_requirements(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    project_dir = make_project(
        tmpdir, requires=["simplewheel==1.0"], backend="test_backend"
    )
    script.pip("install", "simplewheel==2.0", "--no-index", "-f", data.packages)
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.backends,
        "-f",
        data.packages,
        "--no-build-isolation",
        "--check-build-dependencies",
        project_dir,
        expect_error=True,
    )
    msg = (
        f"Some build dependencies for {project_dir.as_uri()} conflict with the backend "
        "dependencies: simplewheel==2.0 is incompatible with "
        "simplewheel==1.0."
    )
    assert result.returncode != 0
    assert msg in result.stderr, str(result)


def test_pep517_backend_requirements_satisfied_by_prerelease(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    create_basic_wheel_for_package(script, "myreq", "1.0a1")
    script.pip("install", "myreq==1.0a1", "--no-index", "-f", script.scratch_path)
    script.pip("install", "test_backend", "--no-index", "-f", data.backends)

    project_dir = make_project(
        script.temp_path,
        requires=["test_backend", "myreq"],
        backend="test_backend",
    )
    project_dir.joinpath("backend_reqs.txt").write_text("myreq")

    result = script.pip("install", "--no-index", "--no-build-isolation", project_dir)
    assert "Installing backend dependencies:" not in result.stdout


def test_pep517_backend_requirements_already_satisfied(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    project_dir = make_project(
        tmpdir, requires=["test_backend", "simplewheel==1.0"], backend="test_backend"
    )
    project_dir.joinpath("backend_reqs.txt").write_text("simplewheel")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.backends,
        "-f",
        data.packages,
        project_dir,
    )
    assert "Installing backend dependencies:" not in result.stdout


def test_pep517_install_with_no_cache_dir(
    script: PipTestEnvironment, tmpdir: Path, data: TestData
) -> None:
    """Check builds with a custom backends work, even with no cache."""
    project_dir = make_project(
        tmpdir, requires=["test_backend"], backend="test_backend"
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-f",
        data.backends,
        project_dir,
    )
    result.assert_installed("project", editable=False)


def make_pyproject_with_setup(
    tmpdir: Path, build_system: bool = True, set_backend: bool = True
) -> Tuple[Path, str]:
    project_dir = tmpdir / "project"
    project_dir.mkdir()
    setup_script = "from setuptools import setup\n"
    expect_script_dir_on_path = True
    if build_system:
        buildsys: Dict[str, Any] = {
            "requires": ["setuptools", "wheel"],
        }
        if set_backend:
            buildsys["build-backend"] = "setuptools.build_meta"
            expect_script_dir_on_path = False
        project_data = tomli_w.dumps({"build-system": buildsys})
    else:
        project_data = ""

    if expect_script_dir_on_path:
        setup_script += "from pep517_test import __version__\n"
    else:
        setup_script += (
            "try:\n"
            "    import pep517_test\n"
            "except ImportError:\n"
            "    pass\n"
            "else:\n"
            '    raise RuntimeError("Source dir incorrectly on sys.path")\n'
        )

    setup_script += 'setup(name="pep517_test", version="0.1", packages=["pep517_test"])'

    project_dir.joinpath("pyproject.toml").write_text(project_data)
    project_dir.joinpath("setup.py").write_text(setup_script)
    package_dir = project_dir / "pep517_test"
    package_dir.mkdir()
    package_dir.joinpath("__init__.py").write_text('__version__ = "0.1"')
    return project_dir, "pep517_test"


def test_no_build_system_section(
    script: PipTestEnvironment, tmpdir: Path, data: TestData, common_wheels: Path
) -> None:
    """Check builds with setup.py, pyproject.toml, but no build-system section."""
    project_dir, name = make_pyproject_with_setup(tmpdir, build_system=False)
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-f",
        common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)


def test_no_build_backend_entry(
    script: PipTestEnvironment, tmpdir: Path, data: TestData, common_wheels: Path
) -> None:
    """Check builds with setup.py, pyproject.toml, but no build-backend entry."""
    project_dir, name = make_pyproject_with_setup(tmpdir, set_backend=False)
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-f",
        common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)


def test_explicit_setuptools_backend(
    script: PipTestEnvironment, tmpdir: Path, data: TestData, common_wheels: Path
) -> None:
    """Check builds with setup.py, pyproject.toml, and a build-backend entry."""
    project_dir, name = make_pyproject_with_setup(tmpdir)
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-f",
        common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)


@pytest.mark.network
def test_pep517_and_build_options(
    script: PipTestEnvironment, tmpdir: Path, data: TestData, common_wheels: Path
) -> None:
    """Backend generated requirements are installed in the build env"""
    project_dir, name = make_pyproject_with_setup(tmpdir)
    result = script.pip(
        "wheel",
        "--wheel-dir",
        tmpdir,
        "--build-option",
        "foo",
        "-f",
        common_wheels,
        project_dir,
        allow_stderr_warning=True,
    )
    assert "Ignoring --build-option when building" in result.stderr
    assert "using PEP 517" in result.stderr


@pytest.mark.network
def test_pep517_and_global_options(
    script: PipTestEnvironment, tmpdir: Path, data: TestData, common_wheels: Path
) -> None:
    """Backend generated requirements are installed in the build env"""
    project_dir, name = make_pyproject_with_setup(tmpdir)
    result = script.pip(
        "wheel",
        "--wheel-dir",
        tmpdir,
        "--global-option",
        "foo",
        "-f",
        common_wheels,
        project_dir,
        allow_stderr_warning=True,
    )
    assert "Ignoring --global-option when building" in result.stderr
    assert "using PEP 517" in result.stderr
