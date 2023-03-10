import shutil
import pytest

from pip._internal.models.direct_url import VcsInfo, ArchiveInfo
from tests.lib import PipTestEnvironment, TestData, _create_test_package
from tests.lib.direct_url import get_created_direct_url


@pytest.mark.usefixtures("with_wheel")
def test_install_find_links_no_direct_url(script: PipTestEnvironment) -> None:
    result = script.pip_install_local("simple")
    assert not get_created_direct_url(result, "simple")

    provenance_url = get_created_direct_url(result, "simple", provenance_file=True)
    assert provenance_url is not None
    assert isinstance(provenance_url.info, ArchiveInfo)
    assert provenance_url.url.startswith("file:///")
    assert provenance_url.info.hash.startswith("sha256=")


@pytest.mark.usefixtures("with_wheel")
def test_install_vcs_editable_no_direct_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    args = ["install", "-e", f"git+{pkg_path.as_uri()}#egg=testpkg"]
    result = script.pip(*args)
    # legacy editable installs do not generate .dist-info,
    # hence no direct_url.json
    assert not get_created_direct_url(result, "testpkg")
    assert not get_created_direct_url(result, "testpkg", provenance_file=True)


@pytest.mark.usefixtures("with_wheel")
def test_install_vcs_non_editable_direct_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    url = pkg_path.as_uri()
    args = ["install", f"git+{url}#egg=testpkg"]
    result = script.pip(*args)
    assert not get_created_direct_url(result, "testpkg", provenance_file=True)
    direct_url = get_created_direct_url(result, "testpkg")
    assert direct_url
    assert direct_url.url == url
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.vcs == "git"


@pytest.mark.usefixtures("with_wheel")
def test_install_archive_direct_url(script: PipTestEnvironment, data: TestData) -> None:
    req = "simple @ " + data.packages.joinpath("simple-2.0.tar.gz").as_uri()
    assert req.startswith("simple @ file://")
    result = script.pip("install", req)
    assert get_created_direct_url(result, "simple")
    assert not get_created_direct_url(result, "simple", provenance_file=True)


@pytest.mark.network
@pytest.mark.usefixtures("with_wheel")
def test_install_vcs_constraint_direct_url(script: PipTestEnvironment) -> None:
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(
        "git+https://github.com/pypa/pip-test-package"
        "@5547fa909e83df8bd743d3978d6667497983a4b7"
        "#egg=pip-test-package"
    )
    result = script.pip("install", "pip-test-package", "-c", constraints_file)
    assert get_created_direct_url(result, "pip_test_package")
    assert not get_created_direct_url(result, "pip_test_package", provenance_file=True)


@pytest.mark.usefixtures("with_wheel")
def test_install_vcs_constraint_direct_file_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    url = pkg_path.as_uri()
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"git+{url}#egg=testpkg")
    result = script.pip("install", "testpkg", "-c", constraints_file)
    assert get_created_direct_url(result, "testpkg")
    assert not get_created_direct_url(result, "testpkg", provenance_file=True)


@pytest.mark.network
@pytest.mark.usefixtures("with_wheel")
def test_install_provenance_url(script: PipTestEnvironment) -> None:
    result = script.pip("install", "INITools==0.2")
    assert not get_created_direct_url(result, "INITools")
    provenance_url = get_created_direct_url(result, "INITools", provenance_file=True)
    assert provenance_url is not None
    assert isinstance(provenance_url.info, ArchiveInfo)
    assert provenance_url.url.startswith("https://files.pythonhosted.org/packages/")
    assert provenance_url.info.hash.startswith("sha256=")


@pytest.mark.usefixtures("with_wheel")
def test_install_find_links_provenance_url(script: PipTestEnvironment, data: TestData) -> None:
    shutil.copy(data.packages / "simple-1.0.tar.gz", script.scratch_path)
    html = script.scratch_path.joinpath("index.html")
    html.write_text('<a href="simple-1.0.tar.gz"></a>')
    result = script.pip(
        "install",
        "simple==1.0",
        "--no-index",
        "--find-links",
        script.scratch_path,
    )
    assert not get_created_direct_url(result, "simple")
    provenance_url = get_created_direct_url(result, "simple", provenance_file=True)
    assert provenance_url is not None
    assert isinstance(provenance_url.info, ArchiveInfo)
    assert provenance_url.url.startswith("file:///")
    assert provenance_url.info.hash.startswith("sha256=")
