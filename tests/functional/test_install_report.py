import json
import textwrap
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from packaging.utils import canonicalize_name

from ..lib import PipTestEnvironment, TestData


def _install_dict(report: Dict[str, Any]) -> Dict[str, Any]:
    return {canonicalize_name(i["metadata"]["name"]): i for i in report["install"]}


def test_install_report_basic(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "simplewheel",
        "--dry-run",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert "install" in report
    assert len(report["install"]) == 1
    simplewheel_report = _install_dict(report)["simplewheel"]
    assert simplewheel_report["metadata"]["name"] == "simplewheel"
    assert simplewheel_report["requested"] is True
    assert simplewheel_report["is_direct"] is False
    url = simplewheel_report["download_info"]["url"]
    assert url.startswith("file://")
    assert url.endswith("/packages/simplewheel-2.0-1-py2.py3-none-any.whl")
    assert (
        simplewheel_report["download_info"]["archive_info"]["hash"]
        == "sha256=71e1ca6b16ae3382a698c284013f66504f2581099b2ce4801f60e9536236ceee"
    )


def test_install_report_dep(
    script: PipTestEnvironment, shared_data: TestData, tmp_path: Path
) -> None:
    """Test dependencies are present in the install report with requested=False."""
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "require_simple",
        "--dry-run",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 2
    assert _install_dict(report)["require-simple"]["requested"] is True
    assert _install_dict(report)["simple"]["requested"] is False


def test_yanked_version(
    script: PipTestEnvironment, data: TestData, tmp_path: Path
) -> None:
    """
    Test is_yanked is True when explicitly requesting a yanked package.
    Yanked files are always ignored, unless they are the only file that
    matches a version specifier that "pins" to an exact version (PEP 592).
    """
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "simple==3.0",
        "--index-url",
        data.index_url("yanked"),
        "--dry-run",
        "--report",
        str(report_path),
        allow_stderr_warning=True,
    )
    report = json.loads(report_path.read_text())
    simple_report = _install_dict(report)["simple"]
    assert simple_report["requested"] is True
    assert simple_report["is_direct"] is False
    assert simple_report["is_yanked"] is True
    assert simple_report["metadata"]["version"] == "3.0"


def test_skipped_yanked_version(
    script: PipTestEnvironment, data: TestData, tmp_path: Path
) -> None:
    """
    Test is_yanked is False when not explicitly requesting a yanked package.
    Yanked files are always ignored, unless they are the only file that
    matches a version specifier that "pins" to an exact version (PEP 592).
    """
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "simple",
        "--index-url",
        data.index_url("yanked"),
        "--dry-run",
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    simple_report = _install_dict(report)["simple"]
    assert simple_report["requested"] is True
    assert simple_report["is_direct"] is False
    assert simple_report["is_yanked"] is False
    assert simple_report["metadata"]["version"] == "2.0"


@pytest.mark.parametrize(
    "specifiers",
    [
        # result should be the same regardless of the method and order in which
        # extras are specified
        ("Paste[openid]==1.7.5.1",),
        ("Paste==1.7.5.1", "Paste[openid]==1.7.5.1"),
        ("Paste[openid]==1.7.5.1", "Paste==1.7.5.1"),
    ],
)
@pytest.mark.network
def test_install_report_index(
    script: PipTestEnvironment, tmp_path: Path, specifiers: Tuple[str, ...]
) -> None:
    """Test report for sdist obtained from index."""
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "--dry-run",
        *specifiers,
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 2
    install_dict = _install_dict(report)
    assert install_dict["paste"]["requested"] is True
    assert install_dict["python-openid"]["requested"] is False
    paste_report = install_dict["paste"]
    assert paste_report["download_info"]["url"].startswith(
        "https://files.pythonhosted.org/"
    )
    assert paste_report["download_info"]["url"].endswith("/Paste-1.7.5.1.tar.gz")
    assert (
        paste_report["download_info"]["archive_info"]["hash"]
        == "sha256=11645842ba8ec986ae8cfbe4c6cacff5c35f0f4527abf4f5581ae8b4ad49c0b6"
    )
    assert paste_report["requested_extras"] == ["openid"]
    assert "requires_dist" in paste_report["metadata"]


@pytest.mark.network
def test_install_report_index_multiple_extras(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """Test report for sdist obtained from index, with multiple extras requested."""
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "--dry-run",
        "Paste[openid]",
        "Paste[subprocess]",
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    install_dict = _install_dict(report)
    assert "paste" in install_dict
    assert install_dict["paste"]["requested_extras"] == ["openid", "subprocess"]


@pytest.mark.network
def test_install_report_direct_archive(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test report for direct URL archive."""
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        str(shared_data.root / "packages" / "simplewheel-1.0-py2.py3-none-any.whl"),
        "--dry-run",
        "--no-index",
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert "install" in report
    assert len(report["install"]) == 1
    simplewheel_report = _install_dict(report)["simplewheel"]
    assert simplewheel_report["metadata"]["name"] == "simplewheel"
    assert simplewheel_report["requested"] is True
    assert simplewheel_report["is_direct"] is True
    url = simplewheel_report["download_info"]["url"]
    assert url.startswith("file://")
    assert url.endswith("/packages/simplewheel-1.0-py2.py3-none-any.whl")
    assert (
        simplewheel_report["download_info"]["archive_info"]["hash"]
        == "sha256=e63aa139caee941ec7f33f057a5b987708c2128238357cf905429846a2008718"
    )
    assert simplewheel_report["download_info"]["archive_info"]["hashes"] == {
        "sha256": "e63aa139caee941ec7f33f057a5b987708c2128238357cf905429846a2008718"
    }


@pytest.mark.network
def test_install_report_vcs_and_wheel_cache(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """Test report for VCS reference, and interactions with the wheel cache."""
    cache_dir = tmp_path / "cache"
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "git+https://github.com/pypa/pip-test-package"
        "@5547fa909e83df8bd743d3978d6667497983a4b7",
        "--cache-dir",
        str(cache_dir),
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 1
    pip_test_package_report = report["install"][0]
    assert pip_test_package_report["is_direct"] is True
    assert pip_test_package_report["requested"] is True
    assert (
        pip_test_package_report["download_info"]["url"]
        == "https://github.com/pypa/pip-test-package"
    )
    assert pip_test_package_report["download_info"]["vcs_info"]["vcs"] == "git"
    assert (
        pip_test_package_report["download_info"]["vcs_info"]["commit_id"]
        == "5547fa909e83df8bd743d3978d6667497983a4b7"
    )
    # Now do it again to make sure the cache is used and that the report still contains
    # the original VCS url.
    report_path.unlink()
    result = script.pip(
        "install",
        "pip-test-package @ git+https://github.com/pypa/pip-test-package"
        "@5547fa909e83df8bd743d3978d6667497983a4b7",
        "--ignore-installed",
        "--cache-dir",
        str(cache_dir),
        "--report",
        str(report_path),
    )
    assert "Using cached pip_test_package" in result.stdout
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 1
    pip_test_package_report = report["install"][0]
    assert pip_test_package_report["is_direct"] is True
    assert pip_test_package_report["requested"] is True
    assert (
        pip_test_package_report["download_info"]["url"]
        == "https://github.com/pypa/pip-test-package"
    )
    assert pip_test_package_report["download_info"]["vcs_info"]["vcs"] == "git"
    assert (
        pip_test_package_report["download_info"]["vcs_info"]["commit_id"]
        == "5547fa909e83df8bd743d3978d6667497983a4b7"
    )


@pytest.mark.network
def test_install_report_vcs_editable(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """Test report remote editable."""
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "--editable",
        "git+https://github.com/pypa/pip-test-package"
        "@5547fa909e83df8bd743d3978d6667497983a4b7"
        "#egg=pip-test-package",
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 1
    pip_test_package_report = report["install"][0]
    assert pip_test_package_report["is_direct"] is True
    assert pip_test_package_report["download_info"]["url"].startswith("file://")
    assert pip_test_package_report["download_info"]["url"].endswith(
        "/src/pip-test-package"
    )
    assert pip_test_package_report["download_info"]["dir_info"]["editable"] is True


@pytest.mark.network
def test_install_report_local_path_with_extras(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test report remote editable."""
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [project]
            name = "pkga"
            version = "1.0"

            [project.optional-dependencies]
            test = ["simple"]
            """
        )
    )
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "--dry-run",
        "--no-build-isolation",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        "--report",
        str(report_path),
        str(project_path) + "[test]",
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 2
    pkga_report = report["install"][0]
    assert pkga_report["metadata"]["name"] == "pkga"
    assert pkga_report["is_direct"] is True
    assert pkga_report["requested"] is True
    assert pkga_report["requested_extras"] == ["test"]
    simple_report = report["install"][1]
    assert simple_report["metadata"]["name"] == "simple"
    assert simple_report["is_direct"] is False
    assert simple_report["requested"] is False
    assert "requested_extras" not in simple_report


@pytest.mark.network
def test_install_report_editable_local_path_with_extras(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test report remote editable."""
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [project]
            name = "pkga"
            version = "1.0"

            [project.optional-dependencies]
            test = ["simple"]
            """
        )
    )
    report_path = tmp_path / "report.json"
    script.pip(
        "install",
        "--dry-run",
        "--no-build-isolation",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        "--report",
        str(report_path),
        "--editable",
        str(project_path) + "[test]",
    )
    report = json.loads(report_path.read_text())
    assert len(report["install"]) == 2
    pkga_report = report["install"][0]
    assert pkga_report["metadata"]["name"] == "pkga"
    assert pkga_report["is_direct"] is True
    assert pkga_report["requested"] is True
    assert pkga_report["requested_extras"] == ["test"]
    simple_report = report["install"][1]
    assert simple_report["metadata"]["name"] == "simple"
    assert simple_report["is_direct"] is False
    assert simple_report["requested"] is False
    assert "requested_extras" not in simple_report


def test_install_report_to_stdout(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    result = script.pip(
        "install",
        "simplewheel",
        "--quiet",
        "--dry-run",
        "--no-index",
        "--find-links",
        str(shared_data.root / "packages/"),
        "--report",
        "-",
    )
    report = json.loads(result.stdout)
    assert "install" in report
    assert len(report["install"]) == 1
