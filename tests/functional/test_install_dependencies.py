import textwrap
from pathlib import Path

import pytest

from tests.lib import (
    PipTestEnvironment,
    TestData,
    TestFailure,
    create_basic_wheel_for_package,
)


@pytest.fixture
def reqs_test_package(tmp_path: Path) -> Path:
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """\
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
            """
        )
    )
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


def test_install_only_deps(
    script: PipTestEnvironment, reqs_test_package: Path, shared_data: TestData
) -> None:
    """Test installing project dependencies."""
    result = script.pip_install_local(
        "--only-deps",
        str(reqs_test_package),
    )
    result.assert_installed("simple", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("pkga", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("simple2", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("child", editable=False, editable_vcs=False)


def test_install_only_deps_does_not_prepare_a_build_env(
    script: PipTestEnvironment, reqs_test_package: Path, shared_data: TestData
) -> None:
    """Test installing project dependencies."""
    result = script.pip_install_local(
        "--only-deps",
        str(reqs_test_package),
    )
    assert "setuptools" not in result.stderr, result.stderr
    result.assert_installed("simple", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("pkga", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("simple2", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("child", editable=False, editable_vcs=False)


def test_install_only_deps_and_extras(
    script: PipTestEnvironment, reqs_test_package: Path, shared_data: TestData
) -> None:
    """Test installing project and extras."""
    result = script.pip_install_local(
        "--only-deps",
        str(reqs_test_package) + "[doc]",
    )
    result.assert_installed("simple", editable=False, editable_vcs=False)
    result.assert_installed("simple2", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("pkga", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("child", editable=False, editable_vcs=False)


def test_install_only_deps_for_wheel(
    script: PipTestEnvironment, reqs_test_package_wheel: Path, shared_data: TestData
) -> None:
    """Test installing project dependencies."""
    result = script.pip_install_local(
        "--only-deps",
        str(reqs_test_package_wheel),
    )
    result.assert_installed("simple", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("pkga", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("simple2", editable=False, editable_vcs=False)
    with pytest.raises(TestFailure):
        result.assert_installed("child", editable=False, editable_vcs=False)


def test_install_dependency_options_are_mutually_exclusive(
    script: PipTestEnvironment,
    reqs_test_package: Path,
) -> None:
    """Test dependency options are mutually exclusive."""
    result = script.pip_install_local(
        "--no-deps",
        "--only-deps",
        str(reqs_test_package),
        expect_error=True,
    )
    assert "--no-deps" in result.stderr
    assert "--only-deps" in result.stderr


def test_install_group_options_conflict_with_only_deps(
    script: PipTestEnvironment,
    reqs_test_package: Path,
) -> None:
    """Test dependency options are mutually exclusive."""
    # TODO: change working directory because reasons
    result = script.pip_install_local(
        "--no-deps",
        "--group",
        "dev",
        str(reqs_test_package),
        expect_error=True,
    )
    assert "--no-deps" in result.stderr
    assert "--group" in result.stderr


def test_install_only_deps_incompatible_with_legacy_resolver(
    script: PipTestEnvironment,
    reqs_test_package: Path,
) -> None:
    """Test legacy resolver options conflict with only-deps."""
    result = script.pip_install_local(
        "--use-deprecated",
        "--only-deps",
        str(reqs_test_package),
        expect_error=True,
    )
    assert "--use-deprecated" in result.stderr
    assert "--only-deps" in result.stderr
