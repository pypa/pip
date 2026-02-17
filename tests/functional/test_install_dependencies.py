import textwrap
from pathlib import Path

import pytest

from tests.lib import PipTestEnvironment, create_basic_wheel_for_package


@pytest.fixture
def reqs_test_package(tmp_path: Path) -> Path:
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(textwrap.dedent("""\
            [build-system]
            requires = ["setuptools"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "pkga"
            version = "1.0"
            dependencies = [
              "simple==3.0",
            ]
            [project.optional-dependencies]
            doc = ["simple2==2.0"]

            [dependency-groups]
            dev = ["child==0.1"]
            """))
    return project_path


@pytest.fixture
def reqs_test_package_wheel(script: PipTestEnvironment) -> Path:
    return create_basic_wheel_for_package(
        script,
        "pkga",
        "1.0",
        depends=["simple==3.0"],
        extras={"doc": ["simple2==2.0"]},
    )


def test_install_only_deps(script: PipTestEnvironment, reqs_test_package: Path) -> None:
    """Test installing project dependencies."""
    result = script.pip_install_local(
        str(reqs_test_package),
        "--only-deps",
    )
    result.assert_installed("simple", editable=False)
    result.assert_not_installed("pkga")
    result.assert_not_installed("simple2")
    result.assert_not_installed("child")


def test_install_only_deps_and_extras(
    script: PipTestEnvironment, reqs_test_package: Path
) -> None:
    """Test installing project and extras."""
    result = script.pip_install_local(
        str(reqs_test_package) + "[doc]",
        "--only-deps",
    )
    result.assert_installed("simple", editable=False)
    result.assert_installed("simple2", editable=False)
    result.assert_not_installed("pkga")
    result.assert_not_installed("child")


def test_install_only_deps_and_extras_from_index(
    script: PipTestEnvironment, reqs_test_package: Path
) -> None:
    """Test installing project and extras."""
    result = script.pip_install_local(
        "requires_simple_extra[extra]",
        "--only-deps",
    )
    result.assert_installed("simple", editable=False)
    result.assert_not_installed("requires_simple_extra")


def test_install_only_deps_for_wheel(
    script: PipTestEnvironment, reqs_test_package_wheel: Path
) -> None:
    """Test installing project dependencies."""
    result = script.pip_install_local(
        str(reqs_test_package_wheel),
        "--only-deps",
    )
    result.assert_installed("simple", editable=False)
    result.assert_not_installed("pkga")
    result.assert_not_installed("simple2")
    result.assert_not_installed("child")


def test_install_dependency_options_are_mutually_exclusive(
    script: PipTestEnvironment, reqs_test_package: Path
) -> None:
    """Test dependency options are mutually exclusive."""
    result = script.pip_install_local(
        str(reqs_test_package),
        "--no-deps",
        "--only-deps",
        expect_error=True,
    )
    assert "--no-dep" in result.stderr
    assert "--only-dep" in result.stderr


def test_install_group_options_conflict_with_only_deps(
    script: PipTestEnvironment, reqs_test_package: Path
) -> None:
    """Test dependency options are mutually exclusive."""
    result = script.pip_install_local(
        "--group",
        "dev",
        str(reqs_test_package),
        "--only-deps",
        cwd=reqs_test_package,  # --group needs pyproject.toml in cwd
        expect_error=True,
    )
    assert "--only-dep" in result.stderr
    assert "--group" in result.stderr


def test_install_only_deps_incompatible_with_legacy_resolver(
    script: PipTestEnvironment, reqs_test_package: Path
) -> None:
    """Test legacy resolver options conflict with only-deps."""
    result = script.pip_install_local(
        "--use-deprecated",
        "legacy-resolver",
        str(reqs_test_package),
        "--only-deps",
        expect_error=True,
    )
    assert "--use-deprecated legacy-resolver" in result.stderr
    assert "--only-dep" in result.stderr
