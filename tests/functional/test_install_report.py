import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
from packaging.utils import canonicalize_name

from ..lib import PipTestEnvironment, TestData, TestPipResult


def _install_dict(report: dict[str, Any]) -> dict[str, Any]:
    return {canonicalize_name(i["metadata"]["name"]): i for i in report["install"]}


def _make_project(path: Path, *, name: str, version: str = "1.0") -> Path:
    """Create a minimal PEP 621 project at ``path`` and return ``path``."""
    path.mkdir(parents=True, exist_ok=True)
    path.joinpath("pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n'
    )
    package_dir = path / canonicalize_name(name).replace("-", "_")
    package_dir.mkdir(exist_ok=True)
    package_dir.joinpath("__init__.py").write_text("")
    return path


def _inspect_entry(script: PipTestEnvironment, name: str) -> dict[str, Any]:
    """Return the ``pip inspect`` entry for ``name``."""
    inspect = json.loads(script.pip("inspect").stdout)
    for entry in inspect["installed"]:
        if canonicalize_name(entry["metadata"]["name"]) == canonicalize_name(name):
            return entry
    raise AssertionError(f"{name} not found in pip inspect output")


def _assert_agree(
    script: PipTestEnvironment,
    report: dict[str, Any],
    result: TestPipResult,
    name: str,
) -> dict[str, Any]:
    """``pip install --report``, the recorded ``direct_url.json`` and ``pip inspect``
    must all describe the same install the same way. Returns ``download_info``.
    """
    installed = result.get_created_direct_url(name)
    assert installed is not None, f"no direct_url.json recorded for {name}"
    report_entry = _install_dict(report)[canonicalize_name(name)]
    download_info = report_entry["download_info"]
    assert report_entry["is_direct"] is True
    # report download_info == what pip recorded on disk as direct_url.json ...
    assert download_info == installed.to_dict_compat()
    # ... == what pip inspect serializes back from that same direct_url.json
    assert _inspect_entry(script, name)["direct_url"] == download_info
    # a local directory is a dir_info, never inferred as a VCS checkout
    assert "vcs_info" not in download_info
    return download_info


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
        "--no-build-isolation",
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
        "--no-build-isolation",
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
        "--no-build-isolation",
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


@pytest.mark.network
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
def test_install_report_index(
    script: PipTestEnvironment, tmp_path: Path, specifiers: tuple[str, ...]
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


def test_install_report_local_path_with_extras(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test report remote editable."""
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(textwrap.dedent("""\
            [project]
            name = "pkga"
            version = "1.0"

            [project.optional-dependencies]
            test = ["simple"]
            """))
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
    # The extras drive dependency selection (``simple`` is pulled in) but must
    # not leak into the direct-URL metadata as if they were part of the path.
    assert pkga_report["requested_extras"] == ["test"]
    pkga_download_info = pkga_report["download_info"]
    assert pkga_download_info["url"].endswith("/pkga")
    assert "[" not in pkga_download_info["url"]
    assert pkga_download_info["dir_info"] == {}
    assert "subdirectory" not in pkga_download_info
    simple_report = report["install"][1]
    assert simple_report["metadata"]["name"] == "simple"
    assert simple_report["is_direct"] is False
    assert simple_report["requested"] is False
    assert "requested_extras" not in simple_report


def test_install_report_editable_local_path_with_extras(
    script: PipTestEnvironment, tmp_path: Path, shared_data: TestData
) -> None:
    """Test report remote editable."""
    project_path = tmp_path / "pkga"
    project_path.mkdir()
    project_path.joinpath("pyproject.toml").write_text(textwrap.dedent("""\
            [project]
            name = "pkga"
            version = "1.0"

            [project.optional-dependencies]
            test = ["simple"]
            """))
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
    # Same contract as the non-editable case: extras select ``simple`` but are
    # not folded into the (editable) direct-URL metadata.
    pkga_download_info = pkga_report["download_info"]
    assert pkga_download_info["url"].endswith("/pkga")
    assert "[" not in pkga_download_info["url"]
    assert pkga_download_info["dir_info"] == {"editable": True}
    assert "subdirectory" not in pkga_download_info
    simple_report = report["install"][1]
    assert simple_report["metadata"]["name"] == "simple"
    assert simple_report["is_direct"] is False
    assert simple_report["requested"] is False
    assert "requested_extras" not in simple_report


def test_install_report_local_directory(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """A plain local directory install: --report download_info, the recorded
    direct_url.json and ``pip inspect`` all describe it as the same dir_info."""
    project_path = _make_project(tmp_path / "pkga", name="pkga")
    report_path = tmp_path / "report.json"
    result = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        str(project_path),
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    download_info = _assert_agree(script, report, result, "pkga")
    assert download_info["url"].endswith("/pkga")
    assert download_info["dir_info"] == {}
    assert "subdirectory" not in download_info


def test_install_report_editable_local_directory(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """A PEP 660 editable local directory: the three views agree, and the URL
    is the project directory (editable state lives in ``dir_info.editable``)."""
    project_path = _make_project(tmp_path / "pkga", name="pkga")
    report_path = tmp_path / "report.json"
    result = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        "--editable",
        str(project_path),
        "--report",
        str(report_path),
    )
    report = json.loads(report_path.read_text())
    download_info = _assert_agree(script, report, result, "pkga")
    assert download_info["url"].endswith("/pkga")
    assert download_info["dir_info"] == {"editable": True}
    assert "subdirectory" not in download_info


@pytest.mark.parametrize("editable", [False, True], ids=["not-editable", "editable"])
def test_install_report_local_file_url_with_subdirectory(
    script: PipTestEnvironment, tmp_path: Path, editable: bool
) -> None:
    """A direct-URL requirement with a local ``file://`` URL and a
    ``#subdirectory=`` fragment: the subdirectory is kept out of the URL and in
    the ``subdirectory`` field, identically for the editable and non-editable
    forms, and matches the recorded direct_url.json and ``pip inspect``."""
    outer = tmp_path / "outer"
    outer.mkdir()
    _make_project(outer / "sub", name="subpkg", version="2.0")
    requirement = f"subpkg @ {outer.as_uri()}#subdirectory=sub"
    report_path = tmp_path / "report.json"
    args = ["install", "--no-build-isolation", "--no-index"]
    if editable:
        args.append("--editable")
    args += [requirement, "--report", str(report_path)]
    result = script.pip(*args)
    report = json.loads(report_path.read_text())
    download_info = _assert_agree(script, report, result, "subpkg")
    assert download_info["url"].endswith("/outer")
    assert "/sub" not in download_info["url"]
    assert download_info["subdirectory"] == "sub"
    assert download_info["dir_info"] == ({"editable": True} if editable else {})


@pytest.mark.git
@pytest.mark.parametrize("editable", [False, True], ids=["not-editable", "editable"])
def test_install_report_local_directory_inside_git_checkout(
    script: PipTestEnvironment, tmp_path: Path, editable: bool
) -> None:
    """A local directory that merely happens to live in a git checkout is still
    reported as a local directory (dir_info), never inferred as a VCS checkout,
    in the report, the recorded direct_url.json and ``pip inspect``."""
    project_path = _make_project(tmp_path / "gitpkg", name="gitpkg")
    script.run("git", "init", "-q", cwd=str(project_path))
    report_path = tmp_path / "report.json"
    args = ["install", "--no-build-isolation", "--no-index"]
    if editable:
        args.append("--editable")
    args += [str(project_path), "--report", str(report_path)]
    result = script.pip(*args)
    report = json.loads(report_path.read_text())
    download_info = _assert_agree(script, report, result, "gitpkg")
    assert "vcs_info" not in download_info
    assert "dir_info" in download_info
    assert download_info["dir_info"] == ({"editable": True} if editable else {})
    assert download_info["url"].endswith("/gitpkg")


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
