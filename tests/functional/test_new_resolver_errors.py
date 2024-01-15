import pathlib
import sys

from tests.lib import (
    PipTestEnvironment,
    create_basic_wheel_for_package,
    create_test_package_with_setup,
)


def test_new_resolver_conflict_requirements_file(
    tmpdir: pathlib.Path, script: PipTestEnvironment
) -> None:
    create_basic_wheel_for_package(script, "base", "1.0")
    create_basic_wheel_for_package(script, "base", "2.0")
    create_basic_wheel_for_package(
        script,
        "pkga",
        "1.0",
        depends=["base==1.0"],
    )
    create_basic_wheel_for_package(
        script,
        "pkgb",
        "1.0",
        depends=["base==2.0"],
    )

    req_file = tmpdir.joinpath("requirements.txt")
    req_file.write_text("pkga\npkgb")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-r",
        req_file,
        expect_error=True,
    )

    message = "package versions have conflicting dependencies"
    assert message in result.stderr, str(result)


def test_new_resolver_conflict_constraints_file(
    tmpdir: pathlib.Path, script: PipTestEnvironment
) -> None:
    create_basic_wheel_for_package(script, "pkg", "1.0")

    constraints_file = tmpdir.joinpath("constraints.txt")
    constraints_file.write_text("pkg!=1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "pkg==1.0",
        expect_error=True,
    )

    assert "ResolutionImpossible" in result.stderr, str(result)

    message = "The user requested (constraint) pkg!=1.0"
    assert message in result.stdout, str(result)


def test_new_resolver_requires_python_error(script: PipTestEnvironment) -> None:
    compatible_python = f">={sys.version_info.major}.{sys.version_info.minor}"
    incompatible_python = f"<{sys.version_info.major}.{sys.version_info.minor}"

    pkga = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        python_requires=compatible_python,
    )
    pkgb = create_test_package_with_setup(
        script,
        name="pkgb",
        version="1.0",
        python_requires=incompatible_python,
    )

    # This always fails because pkgb can never be satisfied.
    result = script.pip("install", "--no-index", pkga, pkgb, expect_error=True)

    # The error message should mention the Requires-Python: value causing the
    # conflict, not the compatible one.
    assert incompatible_python in result.stderr, str(result)
    assert compatible_python not in result.stderr, str(result)


def test_new_resolver_checks_requires_python_before_dependencies(
    script: PipTestEnvironment,
) -> None:
    incompatible_python = f"<{sys.version_info.major}.{sys.version_info.minor}"

    pkg_dep = create_basic_wheel_for_package(
        script,
        name="pkg-dep",
        version="1",
    )
    create_basic_wheel_for_package(
        script,
        name="pkg-root",
        version="1",
        # Refer the dependency by URL to prioritise it as much as possible,
        # to test that Requires-Python is *still* inspected first.
        depends=[f"pkg-dep@{pathlib.Path(pkg_dep).as_uri()}"],
        requires_python=incompatible_python,
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg-root",
        expect_error=True,
    )

    # Resolution should fail because of pkg-a's Requires-Python.
    # This check should be done before pkg-b, so pkg-b should never be pulled.
    assert incompatible_python in result.stderr, str(result)
    assert "pkg-b" not in result.stderr, str(result)
