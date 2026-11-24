"""Tests for --only-binary and --no-binary format control flags."""

from __future__ import annotations

from pathlib import Path

from tests.lib import (
    PipTestEnvironment,
    TestData,
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
)
from tests.lib.wheel import make_wheel


def test_order_no_binary_then_only_binary(script: PipTestEnvironment) -> None:
    """Test --no-binary=:all: --only-binary=<package>.

    When the user specifies --no-binary=:all: --only-binary=simple, they
    expect 'simple' to allow wheels (later flag overrides).
    """
    wheel_path = create_basic_wheel_for_package(script, "simple", "1.0")

    # This should allow wheels for 'simple' because --only-binary comes after
    result = script.pip_install_local(
        "--no-binary=:all:",
        "--only-binary=simple",
        "simple==1.0",
        find_links=[wheel_path.parent],
    )
    script.assert_installed(simple="1.0")
    # Should NOT be building from source
    assert "Building wheel for simple" not in result.stdout


def test_order_only_binary_then_no_binary(script: PipTestEnvironment) -> None:
    """Test --only-binary=:all: --no-binary=<package>.

    When the user specifies --only-binary=:all: --no-binary=simple,
    'simple' should be built from source (later flag overrides).
    """
    wheel_path = create_basic_wheel_for_package(script, "simple", "1.0")
    create_basic_sdist_for_package(script, "simple", "1.0")

    # This should build from source for 'simple' because --no-binary comes after
    result = script.pip_install_local(
        "--only-binary=:all:",
        "--no-binary=simple",
        "simple==1.0",
        find_links=[wheel_path.parent],
    )
    script.assert_installed(simple="1.0")
    assert "Building wheel for simple" in result.stdout


def test_reqfile_no_binary_overrides_cmdline_only_binary(
    script: PipTestEnvironment,
) -> None:
    """Test requirements file --no-binary overrides command line --only-binary."""
    wheel_path = create_basic_wheel_for_package(script, "simple", "1.0")
    create_basic_sdist_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {wheel_path.parent.as_posix()}\n"
        "--no-binary :all:\nsimple==1.0\n",
    )

    result = script.pip_install_local(
        "--only-binary=:all:", "-r", req_file, find_links=[]
    )
    script.assert_installed(simple="1.0")
    # Requirements file --no-binary should override CLI --only-binary
    assert "Building wheel for simple" in result.stdout


def test_reqfile_only_binary_overrides_cmdline_no_binary(
    script: PipTestEnvironment,
) -> None:
    """Test requirements file --only-binary overrides command line --no-binary."""
    # Create only a wheel, no sdist
    wheel_path = create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {wheel_path.parent.as_posix()}\n"
        "--only-binary :all:\nsimple==1.0\n",
    )

    result = script.pip_install_local(
        "--no-binary=:all:", "-r", req_file, find_links=[]
    )
    result.assert_installed("simple", editable=False)
    # Requirements file --only-binary should override CLI --no-binary
    assert "Building wheel for simple" not in result.stdout


def test_package_specific_overrides_all_in_requirements_file(
    script: PipTestEnvironment,
) -> None:
    """Test package-specific setting overrides :all: in requirements file."""
    wheel_path = create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {wheel_path.parent.as_posix()}\n--no-binary :all:\n"
        "--only-binary simple\nsimple==1.0\n",
    )

    result = script.pip_install_local("-r", req_file, find_links=[])
    result.assert_installed("simple", editable=False)
    # Package-specific --only-binary should override --no-binary :all:
    assert "Building wheel for simple" not in result.stdout


def test_direct_source_format_control(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    source = data.packages.joinpath("simple-1.0.tar.gz")
    requirement = f"simple @ {source.as_uri()}"

    result = script.pip(
        "install",
        "--dry-run",
        "--no-build-isolation",
        "--no-index",
        "--only-binary=simple",
        requirement,
        expect_error=True,
    )
    assert "No sources permitted for simple" in result.stderr

    script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        requirement,
    )
    script.pip("uninstall", "-y", "simple")

    result = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        "--no-binary=simple",
        requirement,
    )

    assert "Successfully installed simple-1.0" in result.stdout
    assert "Building wheel for simple" not in result.stdout


def test_format_rejection_allows_parent_backtracking(
    script: PipTestEnvironment,
    data: TestData,
    tmp_path: Path,
) -> None:
    source = data.packages.joinpath("simple-1.0.tar.gz")
    make_wheel("parent", "1.0").save_to_dir(tmp_path)
    make_wheel(
        "parent",
        "2.0",
        metadata=(
            "Metadata-Version: 2.1\n"
            "Name: parent\n"
            "Version: 2.0\n"
            f"Requires-Dist: simple @ {source.as_uri()}\n"
        ),
    ).save_to_dir(tmp_path)

    result = script.pip(
        "install",
        "--dry-run",
        "--no-build-isolation",
        "--no-index",
        "--find-links",
        tmp_path,
        "--only-binary=simple",
        "parent",
    )

    assert "Would install parent-1.0" in result.stdout
