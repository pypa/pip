import re

from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, DirectUrl
from tests.lib import _create_test_package, path_to_url


def _get_created_direct_url(result, pkg):
    direct_url_metadata_re = re.compile(
        pkg + r"-[\d\.]+\.dist-info." + DIRECT_URL_METADATA_NAME + r"$"
    )
    for filename in result.files_created:
        if direct_url_metadata_re.search(filename):
            direct_url_path = result.test_env.base_path / filename
            with open(direct_url_path) as f:
                return DirectUrl.from_json(f.read())
    return None


def test_install_find_links_no_direct_url(script, with_wheel):
    result = script.pip_install_local("simple")
    assert not _get_created_direct_url(result, "simple")


def test_install_vcs_editable_no_direct_url(script, with_wheel):
    pkg_path = _create_test_package(script, name="testpkg")
    args = ["install", "-e", "git+%s#egg=testpkg" % path_to_url(pkg_path)]
    result = script.pip(*args)
    # legacy editable installs do not generate .dist-info,
    # hence no direct_url.json
    assert not _get_created_direct_url(result, "testpkg")


def test_install_vcs_non_editable_direct_url(script, with_wheel):
    pkg_path = _create_test_package(script, name="testpkg")
    url = path_to_url(pkg_path)
    args = ["install", "git+{}#egg=testpkg".format(url)]
    result = script.pip(*args)
    direct_url = _get_created_direct_url(result, "testpkg")
    assert direct_url
    assert direct_url.url == url
    assert direct_url.info.vcs == "git"


def test_install_archive_direct_url(script, data, with_wheel):
    req = "simple @ " + path_to_url(data.packages / "simple-2.0.tar.gz")
    assert req.startswith("simple @ file://")
    result = script.pip("install", req)
    assert _get_created_direct_url(result, "simple")
