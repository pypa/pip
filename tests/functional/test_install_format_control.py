"""Tests for --only-binary and --no-binary format control flags.

These tests verify edge case CLI and requirements file interaction behavior,
matching the pattern established by --all-releases and --only-final tests.
"""

from __future__ import annotations

from tests.lib import (
    PipTestEnvironment,
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
)


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
