"""Tests for --all-releases and --only-final release control flags."""

from __future__ import annotations

from tests.lib import PipTestEnvironment, create_basic_wheel_for_package


def test_all_releases_allows_prereleases(script: PipTestEnvironment) -> None:
    """Test that --all-releases :all: allows installing pre-release versions."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    result = script.pip_install_local(
        "--all-releases=:all:", "simple==1.0a1", find_links=[pkg_path.parent]
    )
    result.assert_installed("simple", editable=False)


def test_all_releases_package_specific(script: PipTestEnvironment) -> None:
    """Test --all-releases with package allows pre-releases for that package."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    result = script.pip_install_local(
        "--all-releases=simple", "simple==1.0a1", find_links=[pkg_path.parent]
    )
    result.assert_installed("simple", editable=False)


def test_only_final_blocks_prereleases(script: PipTestEnvironment) -> None:
    """Test that --only-final :all: blocks pre-release versions."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    result = script.pip_install_local(
        "--only-final=:all:",
        "simple==1.0a1",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert (
        "Could not find a final version that satisfies the requirement" in result.stderr
    )


def test_only_final_package_specific(script: PipTestEnvironment) -> None:
    """Test --only-final with package blocks pre-releases for that package."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    result = script.pip_install_local(
        "--only-final=simple",
        "simple==1.0a1",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert (
        "Could not find a final version that satisfies the requirement" in result.stderr
    )


def test_pre_transforms_to_all_releases(script: PipTestEnvironment) -> None:
    """Test that --pre is equivalent to --all-releases :all:."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    result = script.pip_install_local(
        "--pre", "simple==1.0a1", find_links=[pkg_path.parent]
    )
    result.assert_installed("simple", editable=False)


def test_pre_with_all_releases_fails(script: PipTestEnvironment) -> None:
    """Test that --pre cannot be used with --all-releases."""
    result = script.pip(
        "install",
        "--pre",
        "--all-releases=pkg1",
        "dummy",
        expect_error=True,
    )
    assert "--pre cannot be used with --all-releases or --only-final" in result.stderr


def test_pre_with_only_final_fails(script: PipTestEnvironment) -> None:
    """Test that --pre cannot be used with --only-final."""
    result = script.pip(
        "install",
        "--pre",
        "--only-final=pkg1",
        "dummy",
        expect_error=True,
    )
    assert "--pre cannot be used with --all-releases or --only-final" in result.stderr


def test_all_releases_none(script: PipTestEnvironment) -> None:
    """Test that --all-releases :none: empties the set."""
    # Create both a prerelease and a final version
    pre_pkg = create_basic_wheel_for_package(script, "simple", "1.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    # Without specifying exact version, it should install the final version
    # because :none: cleared the :all: setting
    script.pip_install_local(
        "--all-releases=:all:",
        "--all-releases=:none:",
        "simple",
        find_links=[pre_pkg.parent],
    )
    script.assert_installed(simple="1.0")


def test_package_specific_overrides_all(script: PipTestEnvironment) -> None:
    """Test that package-specific --only-final overrides :all: --all-releases."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    # Allow pre-releases for all packages
    result = script.pip_install_local(
        "--all-releases=:all:",
        "--only-final=simple",  # But not for 'simple'
        "simple==1.0a1",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert (
        "Could not find a final version that satisfies the requirement" in result.stderr
    )


def test_requirements_file_all_releases(script: PipTestEnvironment) -> None:
    """Test --all-releases in requirements file."""
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    req_file = script.temporary_file(
        "reqs.txt", "--all-releases :all:\nsimple==1.0a1\n"
    )

    result = script.pip_install_local("-r", req_file, find_links=[pkg_path.parent])
    result.assert_installed("simple", editable=False)


def test_requirements_file_only_final(script: PipTestEnvironment) -> None:
    """Test --only-final in requirements file."""
    # Create both a prerelease and a final version
    pre_pkg = create_basic_wheel_for_package(script, "simple", "1.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    # No specific version
    req_file = script.temporary_file("reqs.txt", "--only-final :all:\nsimple\n")

    script.pip_install_local("-r", req_file, find_links=[pre_pkg.parent])
    # Should install final version, not prerelease
    script.assert_installed(simple="1.0")


def test_order_only_final_then_all_releases(script: PipTestEnvironment) -> None:
    """Test critical case: --only-final=:all: --all-releases=<package>.

    This tests that argument order is preserved when passed to build backends.
    When the user specifies --only-final=:all: --all-releases=simple, they
    expect 'simple' to allow prereleases (later flag overrides).
    """
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    # This should allow prereleases for 'simple' because --all-releases comes after
    result = script.pip_install_local(
        "--only-final=:all:",
        "--all-releases=simple",
        "simple==1.0a1",
        find_links=[pkg_path.parent],
    )
    result.assert_installed("simple", editable=False)


def test_order_all_releases_then_only_final(script: PipTestEnvironment) -> None:
    """Test reverse case: --all-releases=:all: --only-final=<package>.

    This tests that when the user specifies --all-releases=:all: --only-final=simple,
    'simple' should only allow final releases (later flag overrides).
    """
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0a1")

    # This should block prereleases for 'simple' because --only-final comes after
    result = script.pip_install_local(
        "--all-releases=:all:",
        "--only-final=simple",
        "simple==1.0a1",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert (
        "Could not find a final version that satisfies the requirement" in result.stderr
    )


def test_no_matching_version_without_release_control(
    script: PipTestEnvironment,
) -> None:
    """Test error message when no version matches without release control flags.

    This verifies the generic "Could not find a version" message is shown
    when release control isn't restricting to final versions only.
    """
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0")

    # Request a version that doesn't exist, without any release control flags
    result = script.pip_install_local(
        "simple==2.0",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert "Could not find a version that satisfies the requirement" in result.stderr
    # Ensure it's NOT saying "final version"
    assert "Could not find a final version" not in result.stderr


def test_no_matching_version_with_all_releases(
    script: PipTestEnvironment,
) -> None:
    """Test error message when no version matches with --all-releases.

    This verifies the generic "Could not find a version" message is shown
    when --all-releases is used (not restricting to final versions).
    """
    pkg_path = create_basic_wheel_for_package(script, "simple", "1.0")

    # Request a version that doesn't exist, with --all-releases
    result = script.pip_install_local(
        "--all-releases=:all:",
        "simple==2.0",
        find_links=[pkg_path.parent],
        expect_error=True,
    )
    assert "Could not find a version that satisfies the requirement" in result.stderr


def test_pre_flag_with_requirements_file_containing_options(
    script: PipTestEnvironment,
) -> None:
    """Test --pre on command line works with requirements file options.

    Requirements file options overwrote command-line release control.
    """
    pre_pkg = create_basic_wheel_for_package(script, "simple", "2.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {pre_pkg.parent}\nsimple\n",
    )

    report = script.pip_install_local_report("-r", req_file, find_links=[])
    assert len(report["install"]) == 1
    assert report["install"][0]["metadata"]["version"] == "1.0"

    report = script.pip_install_local_report("--pre", "-r", req_file, find_links=[])
    assert len(report["install"]) == 1
    assert report["install"][0]["metadata"]["version"] == "2.0a1"


def test_reqfile_all_releases_overrides_cmdline_only_final(
    script: PipTestEnvironment,
) -> None:
    """Test requirements file --all-releases overrides command line --only-final."""
    pre_pkg = create_basic_wheel_for_package(script, "simple", "2.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {pre_pkg.parent}\n--all-releases :all:\nsimple\n",
    )

    report = script.pip_install_local_report(
        "--only-final=:all:", "-r", req_file, find_links=[]
    )
    assert len(report["install"]) == 1
    assert report["install"][0]["metadata"]["version"] == "2.0a1"


def test_reqfile_only_final_overrides_cmdline_all_releases(
    script: PipTestEnvironment,
) -> None:
    """Test requirements file --only-final overrides command line --all-releases."""
    pre_pkg = create_basic_wheel_for_package(script, "simple", "2.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {pre_pkg.parent}\n--only-final :all:\nsimple\n",
    )

    report = script.pip_install_local_report(
        "--all-releases=:all:", "-r", req_file, find_links=[]
    )
    assert len(report["install"]) == 1
    assert report["install"][0]["metadata"]["version"] == "1.0"


def test_package_specific_overrides_all_in_requirements_file(
    script: PipTestEnvironment,
) -> None:
    """Test package-specific setting overrides :all: in requirements file."""
    pre_pkg = create_basic_wheel_for_package(script, "simple", "2.0a1")
    create_basic_wheel_for_package(script, "simple", "1.0")

    req_file = script.temporary_file(
        "requirements.txt",
        f"--find-links {pre_pkg.parent}\n--all-releases :all:\n"
        "--only-final simple\nsimple\n",
    )

    report = script.pip_install_local_report("-r", req_file, find_links=[])
    assert len(report["install"]) == 1
    assert report["install"][0]["metadata"]["version"] == "1.0"
