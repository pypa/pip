import os
import textwrap
import urllib.parse


def test_find_links_relative_path(script, data, with_wheel):
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


def test_find_links_requirements_file_relative_path(script, data, with_wheel):
    """Test find-links as a relative path to a reqs file."""
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """
        --no-index
        --find-links={}
        parent==0.1
        """.format(
                data.packages.replace(os.path.sep, "/")
            )
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


def test_install_from_file_index_hash_link(script, data, with_wheel):
    """
    Test that a pkg can be installed from a file:// index using a link with a
    hash
    """
    result = script.pip("install", "-i", data.index_url(), "simple==1.0")
    dist_info_folder = script.site_packages / "simple-1.0.dist-info"
    result.did_create(dist_info_folder)


def test_file_index_url_quoting(script, data, with_wheel):
    """
    Test url quoting of file index url with a space
    """
    index_url = data.index_url(urllib.parse.quote("in dex"))
    result = script.pip("install", "-vvv", "--index-url", index_url, "simple")
    result.did_create(script.site_packages / "simple")
    result.did_create(script.site_packages / "simple-1.0.dist-info")
