import shutil
import textwrap

from tests.lib import PipTestEnvironment, TestData


def test_find_links_relative_path(script: PipTestEnvironment, data: TestData) -> None:
    """Test find-links as a relative path."""
    result = script.pip(
        "install",
        "parent==0.1",
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
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            f"""
        --no-index
        --find-links={data.packages.as_posix()}
        parent==0.1
        """
        )
    )
    result = script.pip(
        "install",
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
    result = script.pip("install", "-i", data.index_url(), "simple==1.0")
    dist_info_folder = script.site_packages / "simple-1.0.dist-info"
    result.did_create(dist_info_folder)


def test_file_index_url_quoting(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test url quoting of file index url with a space
    """
    index_url = data.index_url("in dex")
    result = script.pip("install", "-vvv", "--index-url", index_url, "simple")
    result.did_create(script.site_packages / "simple")
    result.did_create(script.site_packages / "simple-1.0.dist-info")
