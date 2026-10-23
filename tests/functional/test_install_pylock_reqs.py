import json
from hashlib import sha256
from pathlib import Path

import pytest
import tomli_w

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.pylock import Package, PackageWheel, Pylock
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from tests.lib import PipTestEnvironment, TestData, make_wheel


@pytest.fixture
def selection_lock(script: PipTestEnvironment) -> Path:
    """Create wheels for defaults and selected groups, including a version switch."""
    records = [
        ("always", "1", None),
        ("runtime", "1", "'runtime' in dependency_groups"),
        ("switch", "1", "'dev' not in dependency_groups"),
        ("switch", "2", "'dev' in dependency_groups"),
        ("extra", "1", "'dev' in extras"),
        ("combined", "1", "'dev' in extras and 'docs' in dependency_groups"),
        (
            "intersection",
            "1",
            "'dev' in dependency_groups and 'docs' in dependency_groups",
        ),
    ]
    packages = []
    for name, version, marker in records:
        wheel_path = Path(make_wheel(name, version).save_to_dir(script.scratch_path))
        packages.append(
            Package(
                name=canonicalize_name(name),
                version=Version(version),
                marker=Marker(marker) if marker is not None else None,
                wheels=[
                    PackageWheel(
                        path=wheel_path.name,
                        hashes={"sha256": sha256(wheel_path.read_bytes()).hexdigest()},
                    )
                ],
            )
        )
    lock = Pylock(
        lock_version=Version("1.0"),
        created_by="pip",
        packages=packages,
        extras=[canonicalize_name("dev")],
        dependency_groups=["dev", "docs"],
        default_groups=["runtime"],
    )
    path = script.scratch_path / "pylock.groups.toml"
    path.write_text(tomli_w.dumps(lock.to_dict()), encoding="utf-8")
    return path


def test_install_pylock_group_without_defaults(
    script: PipTestEnvironment, selection_lock: Path
) -> None:
    script.pip(
        "install",
        "--no-index",
        "--group",
        f"{selection_lock}:dev",
        allow_stderr_warning=True,
    )

    script.assert_installed(always="1", switch="2")
    script.assert_not_installed("runtime", "extra", "intersection")


@pytest.mark.parametrize("lock_option", ["-r", "--group"])
def test_install_pylock_with_implicit_project_group(
    script: PipTestEnvironment, selection_lock: Path, lock_option: str
) -> None:
    script.scratch_path.joinpath("pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["extra==1"]\n'
    )
    source = str(selection_lock)
    if lock_option == "--group":
        source += ":dev"

    script.pip_install_local(
        lock_option,
        source,
        "--group",
        "dev",
        "--no-require-hashes",
        find_links=script.scratch_path,
        allow_stderr_warning=True,
    )

    script.assert_installed(
        always="1", extra="1", switch="1" if lock_option == "-r" else "2"
    )
    if lock_option == "-r":
        script.assert_installed(runtime="1")
    else:
        script.assert_not_installed("runtime")
    script.assert_not_installed("intersection")


@pytest.mark.parametrize("command", ["install", "download"])
def test_pylock_group_rejects_target_interpreter(
    script: PipTestEnvironment, command: str
) -> None:
    arguments = ["--dry-run"] if command == "install" else []
    result = script.pip(
        command,
        "--only-binary=:all:",
        "--python-version=3.10",
        "--group=pylock.toml:dev",
        *arguments,
        expect_error=True,
    )

    assert (
        "not supported when selecting requirements from 'pylock.toml'" in result.stderr
    )


def test_pylock_groups_share_one_selection(
    script: PipTestEnvironment,
    selection_lock: Path,
) -> None:
    destination = script.scratch_path / "output"
    script.pip(
        "download",
        "--no-index",
        "-d",
        destination,
        "--group",
        f"{selection_lock}:dev",
        "-r",
        selection_lock,
        "--group",
        "./pylock.groups.toml:docs",
        "-r",
        "pylock.groups.toml",
        allow_stderr_warning=True,
    )

    assert sorted(wheel.name for wheel in destination.glob("*.whl")) == [
        "always-1-py2.py3-none-any.whl",
        "intersection-1-py2.py3-none-any.whl",
        "runtime-1-py2.py3-none-any.whl",
        "switch-2-py2.py3-none-any.whl",
    ]


@pytest.mark.parametrize(
    "selectors,expected",
    [
        (
            ["-r", "pylock.groups.toml[dev]", "--group", "./pylock.groups.toml:docs"],
            {"always", "combined", "extra", "runtime", "switch"},
        ),
        (
            ["--group", "pylock.groups.toml[dev]:docs"],
            {"always", "combined", "extra", "switch"},
        ),
        (
            [
                "--group",
                "pylock.groups.toml[dev]:dev",
                "--group",
                "./pylock.groups.toml:docs",
                "-r",
                "pylock.groups.toml",
            ],
            {"always", "combined", "extra", "intersection", "runtime", "switch"},
        ),
    ],
)
def test_pylock_extras_and_groups_download(
    script: PipTestEnvironment,
    selection_lock: Path,
    selectors: list[str],
    expected: set[str],
) -> None:
    destination = script.scratch_path / "output"
    script.pip(
        "download",
        "--no-index",
        "-d",
        destination,
        *selectors,
        allow_stderr_warning=True,
    )

    assert {wheel.name.split("-")[0] for wheel in destination.glob("*.whl")} == expected


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


def test_install_pylock_no_require_hashes(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    """Install from pylock with a mix of requirements with hash
    and local directories, with --no-require-hashes."""
    pylock_path = data.lockfiles.joinpath("pylock.mixed.toml")
    cmd: list[str | Path] = [
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
    ]
    # Mixing requirement with hashes and local directory fails because local
    # directory has no hash
    result = script.pip(
        *cmd,
        expect_error=True,
    )
    assert "experimental" in result.stderr
    assert "there is no single file to hash" in result.stderr
    # With --no-require-hashes, it succeeds
    result = script.pip(
        *cmd,
        "--no-require-hashes",
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
            r["download_info"].get("dir_info", {}).get("editable", False),
        )
        for r in installed
    ] == [
        ("simplewheel", "2.0", False, True, False),  # wheel
        ("singlemodule", "0.0.1", True, True, True),  # directory, editable
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


def test_install_remote_pylock_preserves_network_diagnostic(
    script: PipTestEnvironment,
) -> None:
    """Remote pylock network failures should render the diagnostic error."""
    result = script.pip(
        "install",
        "--retries",
        "0",
        "--dry-run",
        "-r",
        "http://127.0.0.1:1/pylock.toml",
        expect_error=True,
    )

    assert "<ConnectionFailedError: connection-failed>" not in result.stderr
    assert "connection-failed" in result.stderr
    assert "127.0.0.1" in result.stderr


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
    assert "Could not install locked package 'simplewheel'" in result.stderr
    assert "No binaries permitted for simplewheel" in result.stderr


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
    assert "Could not install locked package 'simple'" in result.stderr
    assert "No sources permitted for simple" in result.stderr


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


def test_install_pylock_default_prerelease(
    script: PipTestEnvironment,
    shared_data: TestData,
) -> None:
    """Prereleases are allowed by default."""
    pylock_path = shared_data.lockfiles.joinpath("pylock.prerelease-wheel.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install pkg-prerelease-1.0a1" in result.stdout


def test_install_pylock_reject_prerelease(
    script: PipTestEnvironment,
    shared_data: TestData,
) -> None:
    """Prereleases are rejected when --only-final is set."""
    pylock_path = shared_data.lockfiles.joinpath("pylock.prerelease-wheel.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--only-final=pkg-prerelease",
        expect_error=True,
    )
    assert (
        "A pre-release version 1.0a1 is specified in a provided lock file "
        "for pkg-prerelease but only final versions are allowed" in result.stderr
    )


def test_install_pylock_allow_archive_prerelease(
    script: PipTestEnvironment,
    shared_data: TestData,
) -> None:
    """--only-final does not influence direct URL requirements."""
    pylock_path = shared_data.lockfiles.joinpath("pylock.prerelease-archive.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--only-final=pkg-prerelease",
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install pkg-prerelease-1.0a1" in result.stdout


def test_install_pylock_conflict(
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
        "simplewheel<2",  # conflict with simplewheel==2.0 in lock file
        expect_error=True,
    )
    assert (
        "The requirement simplewheel<2 is not compatible with version 2.0 specified "
        "in a provided lock file" in result.stderr
    )


def test_install_pylock_uploaded_prior_to(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.certifi-with-upload_time.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--uploaded-prior-to=2026-01-01",
        expect_error=True,
    )
    assert "Could not install locked package 'certifi' from " in result.stderr
    assert (
        "Upload time 2026-06-17 10:31:06+00:00 not prior to 2026-01-01" in result.stderr
    )


def test_install_pylock_uploaded_prior_to_missing_upload_time(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.certifi-without-upload_time.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--dry-run",
        "-r",
        pylock_path,
        "--uploaded-prior-to=2026-01-01",
        expect_error=True,
    )
    assert (
        "pylock.certifi-without-upload_time.toml does not provide upload-time metadata"
        in result.stderr
    )


def test_install_pylock_with_extras_no_extras(
    script: PipTestEnvironment,
    shared_data: TestData,
) -> None:
    """Installing from a lockfile with extras does not install extras by default."""
    pylock_path = shared_data.lockfiles.joinpath("pylock.withextras.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        shared_data.common_wheels,  # to obtain build backend to build sdist
        "--no-deps",
        "--dry-run",
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install simple-2.0" in result.stdout
    assert "simplewheel" not in result.stdout


def test_install_pylock_with_extras_one_extras(
    script: PipTestEnvironment,
    shared_data: TestData,
) -> None:
    """Installing from a lockfile with extras with one extra selected."""
    pylock_path = shared_data.lockfiles.joinpath("pylock.withextras.toml[extra1]")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        shared_data.common_wheels,  # to obtain build backend to build sdist
        "--no-deps",
        "--dry-run",
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install simple-2.0 simplewheel-2.0" in result.stdout
