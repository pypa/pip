"""Tests for the build constraints feature."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from pip._internal.utils.urls import path_to_url

from tests.lib import (
    PipTestEnvironment,
    TestData,
    TestPipResult,
    create_test_package_with_setup,
)

# Build dependencies can be installed in a subprocess (default) or in process
# (--use-feature=inprocess-build-deps); constraint handling must match for both.
INSTALLER_ARGS = [
    pytest.param([], id="subprocess"),
    pytest.param(["--use-feature=inprocess-build-deps"], id="inprocess"),
]


def _create_simple_test_package(script: PipTestEnvironment, name: str) -> Path:
    """Create a simple test package with minimal setup."""
    return create_test_package_with_setup(
        script,
        name=name,
        version="1.0",
        py_modules=[name],
    )


def _create_constraints_file(
    script: PipTestEnvironment, filename: str, content: str
) -> Path:
    """Create a constraints file with the given content."""
    constraints_file = script.scratch_path / filename
    constraints_file.write_text(content)
    return constraints_file


def _create_pylock_build_constraints_file(
    script: PipTestEnvironment, data: TestData, filename: str, package: str
) -> Path:
    """Create a pylock.toml build-constraints file pinning *package* to
    whichever matching wheel exists in common_wheels, hash computed on
    the spot rather than hardcoded."""
    wheel_candidates = list(data.common_wheels.glob(f"{package}-*.whl"))
    assert len(wheel_candidates) == 1, (
        f"expected exactly one {package} wheel in {data.common_wheels}, "
        f"got {wheel_candidates}"
    )
    wheel_path = wheel_candidates[0]
    digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    # "name==version" parsed from the wheel filename's first two `-`-separated
    # segments, same convention the wheel filename spec itself uses.
    name, version = wheel_path.name.split("-")[:2]

    pylock_path = script.scratch_path / filename
    pylock_path.write_text(f"""\
lock-version = "1.0"
created-by = "pip"

[[packages]]
name = "{name}"
version = "{version}"

[[packages.wheels]]
name = "{wheel_path.name}"
path = "{wheel_path}"

[packages.wheels.hashes]
sha256 = "{digest}"
""")
    return pylock_path


def _run_pip_install_with_build_constraints(
    script: PipTestEnvironment,
    data: TestData,
    project_dir: Path,
    build_constraints_file: Path,
    extra_args: list[str] | None = None,
    expect_error: bool = False,
    **kwargs: Any,
) -> TestPipResult:
    """Run pip install with build constraints and common arguments."""
    args = [
        "--no-cache-dir",
        "--build-constraint",
        str(build_constraints_file),
    ]

    if extra_args:
        args.extend(extra_args)

    args.append(str(project_dir))

    return script.pip_install_local(
        *args,
        expect_error=expect_error,
        build_isolation=True,
        find_links=data.common_wheels,
        **kwargs,
    )


def test_build_constraints_pylock(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """Same as test_build_constraints_basic_functionality_simple, but with
    the build constraint coming from a pylock.toml file instead."""
    project_dir = _create_simple_test_package(
        script=script, name="test_build_constraints_pylock"
    )
    pylock_path = _create_pylock_build_constraints_file(
        script=script,
        data=data,
        filename="pylock.buildconstraint.toml",
        package="setuptools",
    )
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=pylock_path,
        allow_stderr_warning=True,
    )
    # The experimental-pylock warning is logged inside the isolated
    # build-dependency subprocess, not visible in the outer stderr here;
    # the install succeeding proves the constraint was read and enforced.
    result.assert_installed(
        "test-build-constraints-pylock", editable=False, without_files=["."]
    )


def test_build_constraints_basic_functionality_simple(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """Test that build constraints options are accepted and processed."""
    project_dir = _create_simple_test_package(
        script=script, name="test_build_constraints"
    )
    constraints_file = _create_constraints_file(
        script=script, filename="constraints.txt", content="setuptools>=40.0.0\n"
    )
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=constraints_file,
    )
    result.assert_installed(
        "test-build-constraints", editable=False, without_files=["."]
    )


@pytest.mark.network
def test_build_constraints_vs_regular_constraints_simple(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """Test that build constraints and regular constraints work independently."""
    project_dir = create_test_package_with_setup(
        script,
        name="test_isolation",
        version="1.0",
        py_modules=["test_isolation"],
        install_requires=["six"],
    )
    build_constraints_file = _create_constraints_file(
        script=script, filename="build_constraints.txt", content="setuptools>=40.0.0\n"
    )
    regular_constraints_file = _create_constraints_file(
        script=script, filename="constraints.txt", content="six>=1.10.0\n"
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--build-constraint",
        build_constraints_file,
        "--constraint",
        regular_constraints_file,
        "--use-pep517",
        str(project_dir),
        expect_error=False,
    )
    assert "Successfully installed" in result.stdout
    assert "test_isolation" in result.stdout


def test_build_constraints_environment_isolation_simple(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """Test that build constraints work correctly in isolated build environments."""
    project_dir = _create_simple_test_package(script=script, name="test_env_isolation")
    constraints_file = _create_constraints_file(
        script=script, filename="build_constraints.txt", content="setuptools>=40.0.0\n"
    )
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=constraints_file,
        extra_args=["--isolated"],
    )
    result.assert_installed("test-env-isolation", editable=False, without_files=["."])


def test_build_constraints_file_not_found(
    script: PipTestEnvironment, data: TestData, tmpdir: Path
) -> None:
    """Test behavior when build constraints file doesn't exist."""
    project_dir = _create_simple_test_package(
        script=script, name="test_missing_constraints"
    )
    missing_constraints = script.scratch_path / "missing_constraints.txt"
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=missing_constraints,
        expect_error=True,
    )
    assert "Could not open requirements file" in result.stderr
    assert "No such file or directory" in result.stderr


def test_use_feature_build_constraint_is_always_enabled(
    script: PipTestEnvironment,
) -> None:
    """``--use-feature=build-constraint`` is accepted but now a no-op that
    reports the feature is always enabled."""
    result = script.pip(
        "install",
        "--use-feature=build-constraint",
        "--no-index",
        "does-not-exist",
        expect_error=True,
        allow_stderr_warning=True,
    )
    assert "always enabled" in result.stderr
    assert "build-constraint" in result.stderr


@pytest.mark.parametrize("installer_args", INSTALLER_ARGS)
def test_constraints_dont_pass_through(
    script: PipTestEnvironment, data: TestData, tmpdir: Path, installer_args: list[str]
) -> None:
    """PIP_CONSTRAINT must not affect the isolated build env."""
    project_dir = create_test_package_with_setup(
        script,
        name="test_isolation",
        version="1.0",
        py_modules=["test_isolation"],
    )
    constraints = _create_constraints_file(
        script=script, filename="constraints.txt", content="setuptools==2000\n"
    )
    script.environ["PIP_CONSTRAINT"] = path_to_url(str(constraints))
    result = script.pip_install_local(
        "--no-cache-dir",
        *installer_args,
        str(project_dir),
        build_isolation=True,
        find_links=data.common_wheels,
    )
    result.assert_installed("test_isolation", editable=False, without_files=["."])


@pytest.mark.parametrize("installer_args", INSTALLER_ARGS)
def test_constraints_dont_pass_through_with_build_constraints(
    script: PipTestEnvironment, data: TestData, tmpdir: Path, installer_args: list[str]
) -> None:
    """PIP_CONSTRAINT must not affect the build env even when build
    constraints are also passed."""
    project_dir = create_test_package_with_setup(
        script,
        name="test_isolation",
        version="1.0",
        py_modules=["test_isolation"],
    )
    # An impossible regular constraint that would break the build if it leaked.
    constraints = _create_constraints_file(
        script=script, filename="constraints.txt", content="setuptools==2000\n"
    )
    # A satisfiable build constraint.
    build_constraints = _create_constraints_file(
        script=script,
        filename="build_constraints.txt",
        content="setuptools>=40.0.0\n",
    )
    script.environ["PIP_CONSTRAINT"] = path_to_url(str(constraints))
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=build_constraints,
        extra_args=installer_args,
    )
    result.assert_installed("test_isolation", editable=False, without_files=["."])


@pytest.mark.parametrize("installer_args", INSTALLER_ARGS)
def test_build_constraint_is_enforced(
    script: PipTestEnvironment, data: TestData, tmpdir: Path, installer_args: list[str]
) -> None:
    """An unsatisfiable build constraint must make the build fail."""
    project_dir = create_test_package_with_setup(
        script,
        name="test_isolation",
        version="1.0",
        py_modules=["test_isolation"],
    )
    build_constraints = _create_constraints_file(
        script=script, filename="build_constraints.txt", content="setuptools==2000\n"
    )
    result = _run_pip_install_with_build_constraints(
        script=script,
        data=data,
        project_dir=project_dir,
        build_constraints_file=build_constraints,
        extra_args=installer_args,
        expect_error=True,
    )
    assert "setuptools==2000" in result.stderr
