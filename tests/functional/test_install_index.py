import shutil
import textwrap
from pathlib import Path

from tests.lib import PipTestEnvironment, TestData


def _make_project_page(
    index_dir: Path,
    project: str,
    archives: list[Path],
    status: str | None = None,
    reason: str | None = None,
) -> None:
    """Write a Simple API project page, optionally with a PEP 792 status."""
    project_dir = index_dir / project
    project_dir.mkdir(parents=True)
    meta = ""
    if status is not None:
        meta += f'<meta name="pypi:project-status" content="{status}">'
    if reason is not None:
        meta += f'<meta name="pypi:project-status-reason" content="{reason}">'
    anchors = ""
    for archive in archives:
        shutil.copy(archive, project_dir)
        anchors += f'<a href="{archive.name}">{archive.name}</a>'
    project_dir.joinpath("index.html").write_text(
        f"<!DOCTYPE html><html><head>{meta}</head><body>{anchors}</body></html>"
    )


def test_install_warns_about_archived_project(
    script: PipTestEnvironment, data: TestData
) -> None:
    """A user-requested project with an archived status produces a warning."""
    index_dir = script.scratch_path / "index"
    _make_project_page(
        index_dir,
        "simple",
        [data.packages / "simple-1.0.tar.gz"],
        status="archived",
        reason="gone fishing",
    )
    result = script.pip(
        "install",
        "--no-build-isolation",
        "--index-url",
        index_dir.as_uri(),
        "simple",
        allow_stderr_warning=True,
    )
    assert (
        "Project 'simple' is archived: it is not expected to be updated in the "
        "future (reason: gone fishing)" in result.stderr
    )
    result.did_create(script.site_packages / "simple-1.0.dist-info")


def test_install_quarantined_project_shows_status_in_error(
    script: PipTestEnvironment, data: TestData
) -> None:
    """A quarantined project offers no distributions; the resolution error
    is contextualized with the project's status."""
    index_dir = script.scratch_path / "index"
    _make_project_page(
        index_dir,
        "simple",
        [],
        status="quarantined",
        reason="the project is haunted",
    )
    result = script.pip(
        "install",
        "--index-url",
        index_dir.as_uri(),
        "simple",
        expect_error=True,
    )
    assert "No matching distribution found for simple" in result.stderr
    assert (
        "Project 'simple' is quarantined: it is considered generally unsafe "
        "for use (reason: the project is haunted)" in result.stderr
    )


def test_install_does_not_warn_about_transitive_project_status(
    script: PipTestEnvironment, data: TestData
) -> None:
    """Status warnings are only emitted for user-requested projects, not
    for projects pulled in as dependencies."""
    index_dir = script.scratch_path / "index"
    _make_project_page(
        index_dir,
        "requires-source",
        [data.packages / "requires_source-1.0-py2.py3-none-any.whl"],
    )
    _make_project_page(
        index_dir,
        "source",
        [data.packages / "source-1.0.tar.gz"],
        status="deprecated",
        reason="use sink instead",
    )
    result = script.pip(
        "install",
        "--no-build-isolation",
        "--index-url",
        index_dir.as_uri(),
        "requires-source",
        allow_stderr_warning=True,
    )
    assert "deprecated" not in result.stderr
    result.did_create(script.site_packages / "source")


def test_find_links_relative_path(script: PipTestEnvironment, data: TestData) -> None:
    """Test find-links as a relative path."""
    result = script.pip(
        "install",
        "parent==0.1",
        "--no-build-isolation",
        "--no-index",
        "--find-links",
        "packages/",
        cwd=data.root,
    )
    dist_info_folder = script.site_packages / "parent-0.1.dist-info"
    initools_folder = script.site_packages / "parent"
    result.did_create(dist_info_folder)
    result.did_create(initools_folder)


def test_find_links_no_doctype(script: PipTestEnvironment, data: TestData) -> None:
    shutil.copy(data.packages / "simple-1.0.tar.gz", script.scratch_path)
    html = script.scratch_path.joinpath("index.html")
    html.write_text('<a href="simple-1.0.tar.gz"></a>')
    result = script.pip(
        "install",
        "simple==1.0",
        "--no-build-isolation",
        "--no-index",
        "--find-links",
        script.scratch_path,
        expect_stderr=True,
    )
    assert not result.stderr


def test_find_links_requirements_file_relative_path(
    script: PipTestEnvironment, data: TestData
) -> None:
    """Test find-links as a relative path to a reqs file."""
    script.scratch_path.joinpath("test-req.txt").write_text(textwrap.dedent(f"""
        --no-index
        --find-links={data.packages.as_posix()}
        parent==0.1
        """))
    result = script.pip(
        "install",
        "--no-build-isolation",
        "-r",
        script.scratch_path / "test-req.txt",
        cwd=data.root,
    )
    dist_info_folder = script.site_packages / "parent-0.1.dist-info"
    initools_folder = script.site_packages / "parent"
    result.did_create(dist_info_folder)
    result.did_create(initools_folder)


def test_install_from_file_index_hash_link(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that a pkg can be installed from a file:// index using a link with a
    hash
    """
    result = script.pip(
        "install", "--no-build-isolation", "-i", data.index_url(), "simple==1.0"
    )
    dist_info_folder = script.site_packages / "simple-1.0.dist-info"
    result.did_create(dist_info_folder)


def test_file_index_url_quoting(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test url quoting of file index url with a space
    """
    index_url = data.index_url("in dex")
    result = script.pip(
        "install", "--no-build-isolation", "-vvv", "--index-url", index_url, "simple"
    )
    result.did_create(script.site_packages / "simple")
    result.did_create(script.site_packages / "simple-1.0.dist-info")
