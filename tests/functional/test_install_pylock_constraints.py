"""Tests for using pylock.toml files as constraints (-c/--constraint,
PIP_CONSTRAINT, --build-constraint), mirroring the coverage in
test_install_pylock_reqs.py for the analogous -r/--requirement case."""

import json

from tests.lib import PipTestEnvironment, TestData


def test_constraint_pylock_narrows_unpinned_requirement(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """The main target use case: an otherwise-unpinned requirement gets
    narrowed to the exact version+hash recorded in the pylock.toml
    constraint."""
    pylock_path = data.lockfiles.joinpath("pylock.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,
        "--quiet",
        "--report",
        "-",
        "--dry-run",
        "-c",
        pylock_path,
        "simplewheel",
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    report = json.loads(result.stdout)
    installed = report["install"]
    assert [
        (r["metadata"]["name"], r["metadata"]["version"], r["requested"])
        for r in installed
    ] == [("simplewheel", "2.0", True)]


def test_constraint_pylock_unused_entry_not_installed(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """A package constrained via pylock.toml but not required by anything
    else must not be installed -- constraints only narrow, they never
    force installation on their own (same guarantee as classic -c)."""
    pylock_path = data.lockfiles.joinpath("pylock.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,
        "--quiet",
        "--report",
        "-",
        "--dry-run",
        "-c",
        pylock_path,
        "simplewheel",
        allow_stderr_warning=True,
    )
    report = json.loads(result.stdout)
    installed_names = {r["metadata"]["name"] for r in report["install"]}
    # pylock.toml also constrains "simple" (sdist) and "simple2" (archive),
    # neither requested here -- they must be absent.
    assert installed_names == {"simplewheel"}


def test_constraint_pylock_invalid_hash(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.invalidhash.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.find_links,
        "--dry-run",
        "-c",
        pylock_path,
        # Exact-pinned: a bare name fails earlier on HashUnpinned, before
        # reaching the hash-comparison this test exercises. Also covers
        # the hash coming from the constraint for an already-pinned
        # requirement, not from the requirement itself.
        "simple==2.0",
        expect_error=True,
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


def test_constraint_pylock_editable_rejected(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """pylock.toml directory entries marked editable must be rejected as
    constraints, exactly like a classic editable -c entry already is --
    a constraint can only narrow a name+version, never carry install
    instructions of its own."""
    pylock_path = data.lockfiles.joinpath("pylock.directory.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,
        "--dry-run",
        "-c",
        pylock_path,
        "simplewheel",
        expect_error=True,
    )
    assert "Editable requirements are not allowed as constraints" in result.stderr


def test_constraint_pylock_invalid_lockfile(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.invalid.toml")
    result = script.pip(
        "install", "--no-index", "--dry-run", "-c", pylock_path, expect_error=True
    )
    assert "Invalid pylock file" in result.stderr


def test_constraint_pylock_not_found(
    script: PipTestEnvironment,
    tmp_path: object,
) -> None:
    pylock_path = str(tmp_path) + "/pylock.doesnotexist.toml"  # type: ignore[operator]
    result = script.pip(
        "install", "--no-index", "--dry-run", "-c", pylock_path, expect_error=True
    )
    assert "Error reading pylock file" in result.stderr
