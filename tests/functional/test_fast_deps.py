import fnmatch
import json
import os
import pathlib
import re
from os.path import basename
from typing import Iterable

from pip._vendor.packaging.utils import canonicalize_name
from pytest import mark

from pip._internal.utils.misc import hash_file
from tests.lib import PipTestEnvironment, TestData, TestPipResult


def pip(script: PipTestEnvironment, command: str, requirement: str) -> TestPipResult:
    return script.pip(
        command,
        "--prefer-binary",
        "--no-cache-dir",
        "--use-feature=fast-deps",
        requirement,
        allow_stderr_warning=True,
    )


def assert_installed(script: PipTestEnvironment, names: str) -> None:
    list_output = json.loads(script.pip("list", "--format=json").stdout)
    installed = {canonicalize_name(item["name"]) for item in list_output}
    assert installed.issuperset(map(canonicalize_name, names))


@mark.network
@mark.parametrize(
    ("requirement", "expected"),
    (
        ("Paste==3.4.2", ("Paste", "six")),
        ("Paste[flup]==3.4.2", ("Paste", "six", "flup")),
    ),
)
def test_install_from_pypi(
    requirement: str, expected: str, script: PipTestEnvironment
) -> None:
    pip(script, "install", requirement)
    assert_installed(script, expected)


@mark.network
@mark.parametrize(
    ("requirement", "expected"),
    (
        ("Paste==3.4.2", ("Paste-3.4.2-*.whl", "six-*.whl")),
        ("Paste[flup]==3.4.2", ("Paste-3.4.2-*.whl", "six-*.whl", "flup-*")),
    ),
)
def test_download_from_pypi(
    requirement: str, expected: Iterable[str], script: PipTestEnvironment
) -> None:
    result = pip(script, "download", requirement)
    created = [basename(f) for f in result.files_created]
    assert all(fnmatch.filter(created, f) for f in expected)


@mark.network
def test_build_wheel_with_deps(data: TestData, script: PipTestEnvironment) -> None:
    result = pip(script, "wheel", os.fspath(data.packages / "requiresPaste"))
    created = [basename(f) for f in result.files_created]
    assert fnmatch.filter(created, "requirespaste-3.1.4-*.whl")
    assert fnmatch.filter(created, "Paste-3.4.2-*.whl")
    assert fnmatch.filter(created, "six-*.whl")


@mark.network
def test_require_hash(script: PipTestEnvironment, tmp_path: pathlib.Path) -> None:
    reqs = tmp_path / "requirements.txt"
    reqs.write_text(
        "idna==2.10"
        " --hash=sha256:"
        "b97d804b1e9b523befed77c48dacec60e6dcb0b5391d57af6a65a312a90648c0"
        " --hash=sha256:"
        "b307872f855b18632ce0c21c5e45be78c0ea7ae4c15c828c20788b26921eb3f6"
    )
    result = script.pip(
        "download",
        "--use-feature=fast-deps",
        "-r",
        str(reqs),
        allow_stderr_warning=True,
    )
    created = [basename(f) for f in result.files_created]
    assert fnmatch.filter(created, "idna-2.10*")


@mark.network
def test_hash_mismatch(script: PipTestEnvironment, tmp_path: pathlib.Path) -> None:
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("idna==2.10 --hash=sha256:irna")
    result = script.pip(
        "download",
        "--use-feature=fast-deps",
        "-r",
        str(reqs),
        expect_error=True,
    )
    assert "DO NOT MATCH THE HASHES" in result.stderr


@mark.network
def test_hash_mismatch_existing_download_for_metadata_only_wheel(
    script: PipTestEnvironment, tmp_path: pathlib.Path
) -> None:
    """Metadata-only wheels from PEP 658 or fast-deps check for hash matching in
    a separate code path than when the wheel is downloaded all at once. Make sure we
    still check for hash mismatches."""
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("idna==2.10")
    dl_dir = tmp_path / "downloads"
    dl_dir.mkdir()
    idna_wheel = dl_dir / "idna-2.10-py2.py3-none-any.whl"
    idna_wheel.write_text("asdf")
    result = script.pip(
        "download",
        # Ensure that we have a metadata-only dist for idna.
        "--use-feature=fast-deps",
        "-r",
        str(reqs),
        "-d",
        str(dl_dir),
        allow_stderr_warning=True,
    )
    assert re.search(
        r"WARNING: Previously-downloaded file.*has bad hash", result.stderr
    )
    # This is the correct hash for idna==2.10.
    assert (
        hash_file(str(idna_wheel))[0].hexdigest()
        == "b97d804b1e9b523befed77c48dacec60e6dcb0b5391d57af6a65a312a90648c0"
    )
