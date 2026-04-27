import json
from pathlib import Path

from tests.lib import PipTestEnvironment, TestData


def test_install_pylock(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "--quiet",
        "--report",
        "-",
        "--dry-run",
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    report = json.loads(result.stdout)
    installed = sorted(report["install"], key=lambda r: r["metadata"]["name"])
    assert [
        (
            r["metadata"]["name"],
            r["metadata"]["version"],
            r["is_direct"],
            r["requested"],
        )
        for r in installed
    ] == [
        ("simple", "2.0", False, True),  # sdist
        ("simple2", "3.0", True, True),  # archive (direct URL)
        ("simplewheel", "2.0", False, True),  # wheel
    ]


def test_install_pylock_wheel_cache(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """Installing the same sdist twice triggered a hash checking bug."""
    pylock_path = data.lockfiles.joinpath("pylock.onesdist.toml")
    args: list[str | Path] = [
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "-r",
        pylock_path,
    ]
    result = script.pip("install", *args, allow_stderr_warning=True)
    assert "experimental" in result.stderr
    assert "Successfully installed simple-2.0" in result.stdout
    result = script.pip("install", *args, allow_stderr_warning=True)
    assert "Requirement already satisfied: simple==2.0" in result.stdout
    result = script.pip(
        "install", *args, "--ignore-installed", allow_stderr_warning=True
    )
    assert "Successfully installed simple-2.0" in result.stdout


def test_install_pylock_directory(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.directory.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert (
        "Successfully installed simplewheel-2.0 singlemodule-0.0.1\n" in result.stdout
    )
    script.assert_installed_editable("simplewheel")
    script.assert_installed(singlemodule="0.0.1")


def test_install_pylock_invalid_hash(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.invalidhash.toml")
    result = script.pip(
        "install", "--no-index", "--dry-run", "-r", pylock_path, expect_error=True
    )
    assert (
        "Expected sha256 "
        "3a084929238d13bcd3bb928af04f3bac7ca2357d419e29f01459dc848e2d69a0"
        in result.stderr
    )
    assert (
        "Got        3a084929238d13bcd3bb928af04f3bac7ca2357d419e29f01459dc848e2d69a4"
        in result.stderr
    )


def test_install_pylock_not_found(
    script: PipTestEnvironment,
    tmp_path: Path,
) -> None:
    pylock_path = tmp_path / "pylock.doesnotexist.toml"
    result = script.pip(
        "install", "--no-index", "--dry-run", "-r", pylock_path, expect_error=True
    )
    assert "Error reading pylock file" in result.stderr


def test_install_pylock_invalid_lockfile(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.invalid.toml")
    result = script.pip(
        "install", "--no-index", "--dry-run", "-r", pylock_path, expect_error=True
    )
    assert "Invalid pylock file" in result.stderr


def test_install_pylock_select_error(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.oldpython.toml")
    result = script.pip(
        "install", "--no-index", "--dry-run", "-r", pylock_path, expect_error=True
    )
    assert "Cannot select requirements from pylock file" in result.stderr


def test_install_pylock_no_binary(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.onewheel.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--no-binary=simplewheel",
        expect_error=True,
    )
    assert (
        "binaries are not permitted for package 'simplewheel' and "
        "there is no source distribution for it in" in result.stderr
    )


def test_install_pylock_only_binary(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.onesdist.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--only-binary=:all:",
        expect_error=True,
    )
    assert (
        "source distributions are not permitted for package 'simple' and "
        "there is no compatible wheel for it in" in result.stderr
    )


def test_install_pylock_only_binary_ignored_for_archives(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """--only-binary is ignored for direct URL"""
    pylock_path = data.lockfiles.joinpath("pylock.onearchive.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "--dry-run",
        "-r",
        pylock_path,
        "--only-binary=simple2,simplewheel",
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install simple2-3.0" in result.stdout
