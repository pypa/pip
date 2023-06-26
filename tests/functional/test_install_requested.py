import pytest

from tests.lib import PipTestEnvironment, TestData, TestPipResult


def _assert_requested_present(
    script: PipTestEnvironment, result: TestPipResult, name: str, version: str
) -> None:
    dist_info = script.site_packages / f"{name}-{version}.dist-info"
    requested = dist_info / "REQUESTED"
    assert dist_info in result.files_created
    assert requested in result.files_created


def _assert_requested_absent(
    script: PipTestEnvironment, result: TestPipResult, name: str, version: str
) -> None:
    dist_info = script.site_packages / f"{name}-{version}.dist-info"
    requested = dist_info / "REQUESTED"
    assert dist_info in result.files_created
    assert requested not in result.files_created


def test_install_requested_basic(script: PipTestEnvironment, data: TestData) -> None:
    result = script.pip(
        "install", "--no-index", "-f", data.find_links, "require_simple"
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # dependency is not REQUESTED
    _assert_requested_absent(script, result, "simple", "3.0")


def test_install_requested_requirements(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("requirements.txt").write_text("require_simple\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    _assert_requested_absent(script, result, "simple", "3.0")


def test_install_requested_dep_in_requirements(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("requirements.txt").write_text(
        "require_simple\nsimple<3\n"
    )
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must have REQUESTED because it is in requirements.txt
    _assert_requested_present(script, result, "simple", "2.0")


def test_install_requested_reqs_and_constraints(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("requirements.txt").write_text("require_simple\n")
    script.scratch_path.joinpath("constraints.txt").write_text("simple<3\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        "-c",
        script.scratch_path / "constraints.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must not have REQUESTED because it is merely a constraint
    _assert_requested_absent(script, result, "simple", "2.0")


def test_install_requested_in_reqs_and_constraints(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("requirements.txt").write_text(
        "require_simple\nsimple\n"
    )
    script.scratch_path.joinpath("constraints.txt").write_text("simple<3\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        "-c",
        script.scratch_path / "constraints.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must have REQUESTED because it is in requirements.txt
    _assert_requested_present(script, result, "simple", "2.0")


def test_install_requested_from_cli_with_constraint(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("constraints.txt").write_text("simple<3\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-c",
        script.scratch_path / "constraints.txt",
        "simple",
    )
    # simple must have REQUESTED because it was provided on the command line
    _assert_requested_present(script, result, "simple", "2.0")


@pytest.mark.network
def test_install_requested_from_cli_with_url_constraint(
    script: PipTestEnvironment, data: TestData
) -> None:
    script.scratch_path.joinpath("constraints.txt").write_text(
        "pip-test-package @ git+https://github.com/pypa/pip-test-package@0.1.1\n"
    )
    result = script.pip(
        "install",
        "--no-index",
        "-c",
        script.scratch_path / "constraints.txt",
        "pip-test-package",
    )
    # pip-test-package must have REQUESTED because it was provided on the command line
    _assert_requested_present(script, result, "pip_test_package", "0.1.1")
