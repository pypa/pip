import pytest

from pip._internal.models.direct_url import VcsInfo

from tests.lib import PipTestEnvironment, TestData, _create_test_package
from tests.lib.direct_url import get_created_direct_url


def test_install_find_links_no_direct_url(script: PipTestEnvironment) -> None:
    result = script.pip_install_local("simple")
    assert not get_created_direct_url(result, "simple")


def test_install_vcs_editable_no_direct_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    args = ["install", "-e", f"git+{pkg_path.as_uri()}#egg=testpkg"]
    result = script.pip(*args)
    # legacy editable installs do not generate .dist-info,
    # hence no direct_url.json
    assert not get_created_direct_url(result, "testpkg")


def test_install_vcs_non_editable_direct_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    url = pkg_path.as_uri()
    args = ["install", f"git+{url}#egg=testpkg"]
    result = script.pip(*args)
    direct_url = get_created_direct_url(result, "testpkg")
    assert direct_url
    assert direct_url.url == url
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.vcs == "git"


def test_install_archive_direct_url(script: PipTestEnvironment, data: TestData) -> None:
    req = "simple @ " + data.packages.joinpath("simple-2.0.tar.gz").as_uri()
    assert req.startswith("simple @ file://")
    result = script.pip("install", req)
    assert get_created_direct_url(result, "simple")


@pytest.mark.network
def test_install_vcs_constraint_direct_url(script: PipTestEnvironment) -> None:
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(
        "git+https://github.com/pypa/pip-test-package"
        "@5547fa909e83df8bd743d3978d6667497983a4b7"
        "#egg=pip-test-package"
    )
    result = script.pip("install", "pip-test-package", "-c", constraints_file)
    assert get_created_direct_url(result, "pip_test_package")


def test_install_vcs_constraint_direct_file_url(script: PipTestEnvironment) -> None:
    pkg_path = _create_test_package(script.scratch_path, name="testpkg")
    url = pkg_path.as_uri()
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"git+{url}#egg=testpkg")
    result = script.pip("install", "testpkg", "-c", constraints_file)
    assert get_created_direct_url(result, "testpkg")
