"""Tests for the build constraints feature."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.lib import PipTestEnvironment, TestPipResult, create_test_package_with_setup


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


def _run_pip_install_with_build_constraints(
    script: PipTestEnvironment,
    project_dir: Path,
    build_constraints_file: Path,
    extra_args: list[str] | None = None,
    expect_error: bool = False,
) -> TestPipResult:
    """Run pip install with build constraints and common arguments."""
    args = [
        "install",
        "--no-cache-dir",
        "--build-constraint",
        str(build_constraints_file),
        "--use-feature",
        "build-constraint",
    ]

    if extra_args:
        args.extend(extra_args)

    args.append(str(project_dir))

    return script.pip(*args, expect_error=expect_error)


def _assert_successful_installation(result: TestPipResult, package_name: str) -> None:
    """Assert that the package was successfully installed."""
    assert f"Successfully installed {package_name}" in result.stdout


def _run_pip_install_with_build_constraints_no_feature_flag(
    script: PipTestEnvironment,
    project_dir: Path,
    constraints_file: Path,
) -> TestPipResult:
    """Run pip install with build constraints but without the feature flag."""
    return script.pip(
        "install",
        "--build-constraint",
        str(constraints_file),
        str(project_dir),
        expect_error=True,
    )


def test_build_constraints_basic_functionality_simple(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """Test that build constraints options are accepted and processed."""
    project_dir = _create_simple_test_package(
        script=script, name="test_build_constraints"
    )
    constraints_file = _create_constraints_file(
        script=script, filename="constraints.txt", content="setuptools>=40.0.0\n"
    )
    result = _run_pip_install_with_build_constraints(
        script=script, project_dir=project_dir, build_constraints_file=constraints_file
    )
    _assert_successful_installation(
        result=result, package_name="test_build_constraints"
    )


@pytest.mark.network
def test_build_constraints_vs_regular_constraints_simple(
    script: PipTestEnvironment, tmpdir: Path
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
        "--use-feature",
        "build-constraint",
        str(project_dir),
        expect_error=False,
    )
    assert "Successfully installed" in result.stdout
    assert "test_isolation" in result.stdout


@pytest.mark.network
def test_build_constraints_environment_isolation_simple(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """Test that build constraints work correctly in isolated build environments."""
    project_dir = _create_simple_test_package(script=script, name="test_env_isolation")
    constraints_file = _create_constraints_file(
        script=script, filename="build_constraints.txt", content="setuptools>=40.0.0\n"
    )
    result = _run_pip_install_with_build_constraints(
        script=script,
        project_dir=project_dir,
        build_constraints_file=constraints_file,
        extra_args=["--isolated"],
    )
    _assert_successful_installation(result=result, package_name="test_env_isolation")


def test_build_constraints_file_not_found(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """Test behavior when build constraints file doesn't exist."""
    project_dir = _create_simple_test_package(
        script=script, name="test_missing_constraints"
    )
    missing_constraints = script.scratch_path / "missing_constraints.txt"
    result = _run_pip_install_with_build_constraints(
        script=script,
        project_dir=project_dir,
        build_constraints_file=missing_constraints,
    )
    _assert_successful_installation(
        result=result, package_name="test_missing_constraints"
    )


def test_build_constraints_without_feature_flag(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    """Test that --build-constraint requires the feature flag."""
    project_dir = _create_simple_test_package(script=script, name="test_no_feature")
    constraints_file = _create_constraints_file(
        script=script, filename="constraints.txt", content="setuptools==45.0.0\n"
    )
    result = _run_pip_install_with_build_constraints_no_feature_flag(
        script=script, project_dir=project_dir, constraints_file=constraints_file
    )
    assert result.returncode != 0
    assert "build-constraint" in result.stderr.lower()
