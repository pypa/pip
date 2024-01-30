import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Tuple

import pytest
from pip._vendor.packaging.requirements import Requirement

from pip._internal.models.direct_url import DirectUrl
from pip._internal.utils.urls import path_to_url
from tests.lib import (
    PipTestEnvironment,
    TestPipResult,
)


@pytest.fixture(scope="function")
def install_with_generated_html_index(
    script: PipTestEnvironment,
    html_index_for_packages: Path,
    tmpdir: Path,
) -> Callable[..., Tuple[TestPipResult, Dict[str, Any]]]:
    """Execute `pip download` against a generated PyPI index."""
    output_file = tmpdir / "output_file.json"

    def run_for_generated_index(
        args: List[str],
        *,
        dry_run: bool = True,
        allow_error: bool = False,
    ) -> Tuple[TestPipResult, Dict[str, Any]]:
        """
        Produce a PyPI directory structure pointing to the specified packages, then
        execute `pip install --report ... -i ...` pointing to our generated index.
        """
        pip_args = [
            "install",
            *(("--dry-run",) if dry_run else ()),
            "--ignore-installed",
            "--report",
            str(output_file),
            "-i",
            path_to_url(str(html_index_for_packages)),
            *args,
        ]
        result = script.pip(*pip_args, allow_error=allow_error)
        try:
            with open(output_file, "rb") as f:
                report = json.load(f)
        except FileNotFoundError:
            if allow_error:
                report = {}
            else:
                raise
        return (result, report)

    return run_for_generated_index


def iter_dists(report: Dict[str, Any]) -> Iterator[Tuple[Requirement, DirectUrl]]:
    """Parse a (req,url) tuple from each installed dist in the --report json."""
    for inst in report["install"]:
        metadata = inst["metadata"]
        name = metadata["name"]
        version = metadata["version"]
        req = Requirement(f"{name}=={version}")
        direct_url = DirectUrl.from_dict(inst["download_info"])
        yield (req, direct_url)


@pytest.mark.parametrize(
    "requirement_to_install, expected_outputs",
    [
        ("simple2==1.0", ["simple2==1.0", "simple==1.0"]),
        ("simple==2.0", ["simple==2.0"]),
        (
            "colander",
            ["colander==0.9.9", "translationstring==1.1"],
        ),
        (
            "compilewheel",
            ["compilewheel==1.0", "simple==1.0"],
        ),
    ],
)
def test_install_with_metadata(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
    requirement_to_install: str,
    expected_outputs: List[str],
) -> None:
    """Verify that if a data-dist-info-metadata attribute is present, then it is used
    instead of the actual dist's METADATA."""
    _, report = install_with_generated_html_index(
        [requirement_to_install],
    )
    installed = sorted(str(r) for r, _ in iter_dists(report))
    assert installed == expected_outputs


@pytest.mark.parametrize(
    "requirement_to_install, real_hash",
    [
        (
            "simple==3.0",
            "95e0f200b6302989bcf2cead9465cf229168295ea330ca30d1ffeab5c0fed996",
        ),
        (
            "has-script",
            "16ba92d7f6f992f6de5ecb7d58c914675cf21f57f8e674fb29dcb4f4c9507e5b",
        ),
    ],
)
def test_incorrect_metadata_hash(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
    requirement_to_install: str,
    real_hash: str,
) -> None:
    """Verify that if a hash for data-dist-info-metadata is provided, it must match the
    actual hash of the metadata file."""
    result, _ = install_with_generated_html_index(
        [requirement_to_install],
        allow_error=True,
    )
    assert result.returncode != 0
    expected_msg = f"""\
        Expected sha256 WRONG-HASH
             Got        {real_hash}"""
    assert expected_msg in result.stderr


@pytest.mark.parametrize(
    "requirement_to_install, expected_url",
    [
        ("simple2==2.0", "simple2-2.0.tar.gz.metadata"),
        ("priority", "priority-1.0-py2.py3-none-any.whl.metadata"),
    ],
)
def test_metadata_not_found(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
    requirement_to_install: str,
    expected_url: str,
) -> None:
    """Verify that if a data-dist-info-metadata attribute is provided, that pip will
    fetch the .metadata file at the location specified by PEP 658, and error
    if unavailable."""
    result, _ = install_with_generated_html_index(
        [requirement_to_install],
        allow_error=True,
    )
    assert result.returncode != 0
    expected_re = re.escape(expected_url)
    pattern = re.compile(
        f"ERROR: 404 Client Error: FileNotFoundError for url:.*{expected_re}"
    )
    assert pattern.search(result.stderr), (pattern, result.stderr)


def test_produces_error_for_mismatched_package_name_in_metadata(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
) -> None:
    """Verify that the package name from the metadata matches the requested package."""
    result, _ = install_with_generated_html_index(
        ["simple2==3.0"],
        allow_error=True,
    )
    assert result.returncode != 0
    assert (
        "simple2-3.0.tar.gz has inconsistent Name: expected 'simple2', but metadata "
        "has 'not-simple2'"
    ) in result.stdout


@pytest.mark.parametrize(
    "requirement",
    (
        "requires-simple-extra==0.1",
        "REQUIRES_SIMPLE-EXTRA==0.1",
        "REQUIRES....simple-_-EXTRA==0.1",
    ),
)
def test_canonicalizes_package_name_before_verifying_metadata(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
    requirement: str,
) -> None:
    """Verify that the package name from the command line and the package's
    METADATA are both canonicalized before comparison, while the name from the METADATA
    is always used verbatim to represent the installed candidate in --report.

    Regression test for https://github.com/pypa/pip/issues/12038
    """
    _, report = install_with_generated_html_index(
        [requirement],
    )
    reqs = [str(r) for r, _ in iter_dists(report)]
    assert reqs == ["Requires_Simple.Extra==0.1"]


@pytest.mark.parametrize(
    "requirement,err_string",
    (
        # It's important that we verify pip won't even attempt to fetch the file, so we
        # construct an input that will cause it to error if it tries at all.
        (
            "complex-dist==0.1",
            "Could not install packages due to an OSError: [Errno 2] No such file or directory",  # noqa: E501
        ),
        ("corruptwheel==1.0", ".whl is invalid."),
    ),
)
def test_dry_run_avoids_downloading_metadata_only_dists(
    install_with_generated_html_index: Callable[
        ..., Tuple[TestPipResult, Dict[str, Any]]
    ],
    requirement: str,
    err_string: str,
) -> None:
    """Verify that the underlying dist files are not downloaded at all when
    `install --dry-run` is used to resolve dists with PEP 658 metadata."""
    _, report = install_with_generated_html_index(
        [requirement],
    )
    assert [requirement] == [str(r) for r, _ in iter_dists(report)]
    result, _ = install_with_generated_html_index(
        [requirement],
        dry_run=False,
        allow_error=True,
    )
    assert result.returncode != 0
    assert err_string in result.stderr
