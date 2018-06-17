"""Tests for various classes in pip._internal.models
"""

from pip._vendor.packaging.version import parse as parse_version

from pip._internal.models import index, candidate


class TestPackageIndex(object):
    """Tests for pip._internal.models.index.PackageIndex
    """

    def test_gives_right_urls(self):
        url = "https://mypypi.internal/path/"
        pack_index = index.PackageIndex(url)

        assert pack_index.netloc == "mypypi.internal"
        assert pack_index.url == url
        assert pack_index.simple_url == url + "simple"
        assert pack_index.pypi_url == url + "pypi"

    def test_PyPI_urls_are_correct(self):
        pack_index = index.PyPI

        assert pack_index.netloc == "pypi.org"
        assert pack_index.url == "https://pypi.org/"
        assert pack_index.simple_url == "https://pypi.org/simple"
        assert pack_index.pypi_url == "https://pypi.org/pypi"


class TestInstallationCandidate(object):

    def test_sets_correct_variables(self):
        obj = candidate.InstallationCandidate(
            "A", "1.0.0", "https://somewhere.com/path/A-1.0.0.tar.gz"
        )
        assert obj.project == "A"
        assert obj.version == parse_version("1.0.0")
        assert obj.location == "https://somewhere.com/path/A-1.0.0.tar.gz"

    # NOTE: This isn't checking the ordering logic; only the data provided to
    #       it is correct.
    def test_sets_the_right_key(self):
        obj = candidate.InstallationCandidate(
            "A", "1.0.0", "https://somewhere.com/path/A-1.0.0.tar.gz"
        )
        assert obj._key == (obj.project, obj.version, obj.location)
