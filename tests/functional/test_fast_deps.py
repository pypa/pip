import fnmatch
import json
import os
import pathlib
import re
from collections.abc import Iterable
from os.path import basename
from pathlib import Path

import pytest

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.misc import hash_file

from tests.conftest import HTMLIndexWithRangeServer, RangeHandler
from tests.lib import PipTestEnvironment, TestData, TestPipResult


def pip(script: PipTestEnvironment, command: str, requirement: str) -> TestPipResult:
    return script.pip(
        command,
        "--prefer-binary",
        "--no-cache-dir",
        "--use-feature=fast-deps",
        requirement,
        # TODO: remove this when fast-deps is on by default.
        allow_stderr_warning=True,
    )


def assert_installed(script: PipTestEnvironment, names: str) -> None:
    list_output = json.loads(script.pip("list", "--format=json").stdout)
    installed = {canonicalize_name(item["name"]) for item in list_output}
    assert installed.issuperset(map(canonicalize_name, names))


@pytest.mark.network
@pytest.mark.parametrize(
    "requirement, expected",
    [
        ("Paste==3.4.2", ("Paste", "six")),
        ("Paste[flup]==3.4.2", ("Paste", "six", "flup")),
    ],
)
def test_install_from_pypi(
    requirement: str, expected: str, script: PipTestEnvironment
) -> None:
    pip(script, "install", requirement)
    assert_installed(script, expected)


@pytest.mark.network
@pytest.mark.parametrize(
    "requirement, url, expected",
    [
        (
            "wcwidth==0.2.1",
            "https://files.pythonhosted.org/packages/6c/a6/cdb485093ad4017d874d7a2e6a736d02720258f57876548eea2bf04c76f0/wcwidth-0.2.1-py2.py3-none-any.whl",
            "multiple .dist-info directories found",
        ),
    ],
)
def test_invalid_wheel_parse_error(
    requirement: str, url: str, expected: str, script: PipTestEnvironment
) -> None:
    """Check for both the full download URL and the reason for the error."""
    result = script.pip(
        "install",
        "--use-feature=fast-deps",
        requirement,
        expect_error=True,
    )
    assert url in result.stderr
    assert expected in result.stderr


@pytest.mark.network
@pytest.mark.parametrize(
    "requirement, expected",
    [
        ("Paste==3.4.2", ("Paste-3.4.2-*.whl", "six-*.whl")),
        ("Paste[flup]==3.4.2", ("Paste-3.4.2-*.whl", "six-*.whl", "flup-*")),
    ],
)
def test_download_from_pypi(
    requirement: str, expected: Iterable[str], script: PipTestEnvironment
) -> None:
    result = pip(script, "download", requirement)
    created = [basename(f) for f in result.files_created]
    assert all(fnmatch.filter(created, f) for f in expected)


@pytest.mark.network
def test_build_wheel_with_deps(data: TestData, script: PipTestEnvironment) -> None:
    result = pip(script, "wheel", os.fspath(data.packages / "requiresPaste"))
    created = [basename(f) for f in result.files_created]
    assert fnmatch.filter(created, "requirespaste-3.1.4-*.whl")
    assert fnmatch.filter(created, "Paste-3.4.2-*.whl")
    assert fnmatch.filter(created, "six-*.whl")


@pytest.mark.network
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


@pytest.mark.network
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


@pytest.mark.network
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


@pytest.mark.parametrize("range_handler", list(RangeHandler))
def test_download_range(
    script: PipTestEnvironment,
    tmpdir: Path,
    html_index_with_range_server: HTMLIndexWithRangeServer,
    range_handler: RangeHandler,
) -> None:
    """Execute `pip download` against a generated PyPI index."""
    download_dir = tmpdir / "download_dir"

    def run_for_generated_index(server_port: int, args: list[str]) -> TestPipResult:
        """
        Produce a PyPI directory structure pointing to the specified packages, then
        execute `pip download -i ...` pointing to our generated index.
        """
        pip_args = [
            "download",
            "--use-feature=fast-deps",
            "-d",
            str(download_dir),
            "-i",
            f"http://localhost:{server_port}",
            *args,
        ]
        return script.pip(*pip_args, allow_stderr_warning=True)

    with html_index_with_range_server(range_handler) as (handler, server_port):
        run_for_generated_index(
            server_port,
            ["colander", "compilewheel==2.0", "has-script", "translationstring==0.1"],
        )
        generated_files = os.listdir(download_dir)
        assert fnmatch.filter(generated_files, "colander*.whl")
        assert fnmatch.filter(generated_files, "compilewheel*.whl")
        assert fnmatch.filter(generated_files, "has.script*.whl")
        assert fnmatch.filter(generated_files, "translationstring*.whl")

        colander_wheel_path = "/colander/colander-0.9.9-py2.py3-none-any.whl"
        compile_wheel_path = "/compilewheel/compilewheel-2.0-py2.py3-none-any.whl"
        has_script_path = "/has-script/has.script-1.0-py2.py3-none-any.whl"
        translationstring_path = (
            "/translationstring/translationstring-0.1-py2.py3-none-any.whl"
        )

        if range_handler == RangeHandler.Always200OK:
            assert not handler.head_request_paths
            assert not handler.positive_range_request_paths
            assert {colander_wheel_path} == handler.negative_range_request_paths
            # Tries a range request, finds it's unsupported, so doesn't try it again.
            assert handler.get_request_counts[colander_wheel_path] == 2
            assert handler.ok_response_counts[colander_wheel_path] == 2
            assert handler.get_request_counts[compile_wheel_path] == 1
            assert handler.ok_response_counts[compile_wheel_path] == 1
            assert handler.get_request_counts[has_script_path] == 1
            assert handler.ok_response_counts[has_script_path] == 1
            assert handler.get_request_counts[translationstring_path] == 1
            assert handler.ok_response_counts[translationstring_path] == 1
        elif range_handler == RangeHandler.NoNegativeRange:
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
            } == handler.head_request_paths
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
            } == handler.positive_range_request_paths
            # Tries this first, finds that negative offsets are unsupported, so doesn't
            # try it again.
            assert {colander_wheel_path} == handler.negative_range_request_paths
            # Two more for the first wheel, because it has the failing negative
            # byte request and is larger than the initial chunk size.
            assert handler.get_request_counts[colander_wheel_path] == 4
            assert handler.ok_response_counts[colander_wheel_path] == 2
            # The .dist-info dir at the start requires an additional ranged GET vs
            # translationstring.
            assert handler.get_request_counts[compile_wheel_path] == 3
            assert handler.ok_response_counts[compile_wheel_path] == 2
            # The entire file should have been pulled in with a single ranged GET.
            assert handler.get_request_counts[has_script_path] == 2
            assert handler.ok_response_counts[has_script_path] == 2
            # The entire .dist-info dir should have been pulled in with a single
            # ranged GET. The second GET is for the end of the download, pulling down
            # the entire file contents.
            assert handler.get_request_counts[translationstring_path] == 2
            assert handler.ok_response_counts[translationstring_path] == 2
        elif range_handler == RangeHandler.SneakilyCoerceNegativeRange:
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
            } == handler.head_request_paths
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
            } == handler.positive_range_request_paths
            # Tries this first, finds that negative offsets are unsupported, so doesn't
            # try it again.
            assert {colander_wheel_path} == handler.negative_range_request_paths
            # Two more for the first wheel, because it has the failing negative
            # byte request and is larger than the initial chunk size.
            assert handler.get_request_counts[colander_wheel_path] == 4
            assert handler.ok_response_counts[colander_wheel_path] == 2
            # The .dist-info dir at the start requires an additional ranged GET vs
            # translationstring.
            assert handler.get_request_counts[compile_wheel_path] == 3
            assert handler.ok_response_counts[compile_wheel_path] == 2
            # The entire file should have been pulled in with a single ranged GET.
            assert handler.get_request_counts[has_script_path] == 2
            assert handler.ok_response_counts[has_script_path] == 2
            # The entire .dist-info dir should have been pulled in with a single
            # ranged GET. The second GET is for the end of the download, pulling down
            # the entire file contents.
            assert handler.get_request_counts[translationstring_path] == 2
            assert handler.ok_response_counts[translationstring_path] == 2
        elif range_handler == RangeHandler.SupportsNegativeRange:
            # The negative byte index worked, so no head requests.
            assert not handler.head_request_paths
            # The negative range request was in bounds and pulled in the entire
            # .dist-info directory (at the end of the zip) for translationstring==0.1,
            # so we didn't need another range request for it. compilewheel==2.0 has the
            # .dist-info dir at the start of the zip, so we still need another request
            # for that.
            assert {
                colander_wheel_path,
                has_script_path,
                compile_wheel_path,
            } == handler.positive_range_request_paths
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
            } == handler.negative_range_request_paths
            assert handler.get_request_counts[colander_wheel_path] == 3
            assert handler.ok_response_counts[colander_wheel_path] == 1
            # One more than translationstring, because the .dist-info dir is at the
            # front of the wheel.
            assert handler.get_request_counts[compile_wheel_path] == 3
            assert handler.ok_response_counts[compile_wheel_path] == 1
            # One more than NoNegativeRange, because the negative byte index failed.
            assert handler.get_request_counts[has_script_path] == 3
            assert handler.ok_response_counts[has_script_path] == 1
            assert handler.get_request_counts[translationstring_path] == 2
            assert handler.ok_response_counts[translationstring_path] == 1
        else:
            assert range_handler == RangeHandler.NegativeRangeOverflowing
            # The negative byte index worked, so no head requests.
            assert not handler.head_request_paths
            # The negative range request was in bounds and pulled in the entire
            # .dist-info directory (at the end of the zip) for translationstring==0.1,
            # so we didn't need another range request for it. compilewheel==2.0 has the
            # .dist-info dir at the start of the zip, so we still need another request
            # for that.
            assert {
                colander_wheel_path,
                compile_wheel_path,
            } == handler.positive_range_request_paths
            assert {
                colander_wheel_path,
                compile_wheel_path,
                has_script_path,
                translationstring_path,
                has_script_path,
            } == handler.negative_range_request_paths
            assert handler.get_request_counts[colander_wheel_path] == 3
            assert handler.ok_response_counts[colander_wheel_path] == 1
            # One more than translationstring, because the .dist-info dir is at the
            # front of the wheel.
            assert handler.get_request_counts[compile_wheel_path] == 3
            assert handler.ok_response_counts[compile_wheel_path] == 1
            # One *less* request for has-script than SupportsNegativeRange, because the
            # server returned a full 200 OK response when the negative byte range was
            # larger than the actual file size.
            assert handler.get_request_counts[has_script_path] == 2
            assert handler.ok_response_counts[has_script_path] == 2
            assert handler.get_request_counts[translationstring_path] == 2
            assert handler.ok_response_counts[translationstring_path] == 1
