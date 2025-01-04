"""Tests for various classes in pip._internal.models
"""

from pip._vendor.packaging.version import parse as parse_version

from pip._internal.models import candidate, index
from pip._internal.models.link import Link


class TestPackageIndex:
    """Tests for pip._internal.models.index.PackageIndex"""

    def test_gives_right_urls(self) -> None:
        url = "https://mypypi.internal/path/"
        file_storage_domain = "files.mypypi.internal"
        pack_index = index.PackageIndex(url, file_storage_domain)

        assert pack_index.url == url
        assert pack_index.file_storage_domain == file_storage_domain

        assert pack_index.netloc == "mypypi.internal"
        assert pack_index.simple_url == url + "simple"
        assert pack_index.pypi_url == url + "pypi"

    def test_PyPI_urls_are_correct(self) -> None:
        pack_index = index.PyPI

        assert pack_index.netloc == "pypi.org"
        assert pack_index.url == "https://pypi.org/"
        assert pack_index.simple_url == "https://pypi.org/simple"
        assert pack_index.pypi_url == "https://pypi.org/pypi"
        assert pack_index.file_storage_domain == "files.pythonhosted.org"

    def test_TestPyPI_urls_are_correct(self) -> None:
        pack_index = index.TestPyPI

        assert pack_index.netloc == "test.pypi.org"
        assert pack_index.url == "https://test.pypi.org/"
        assert pack_index.simple_url == "https://test.pypi.org/simple"
        assert pack_index.pypi_url == "https://test.pypi.org/pypi"
        assert pack_index.file_storage_domain == "test-files.pythonhosted.org"


class TestInstallationCandidate:
    def test_sets_correct_variables(self) -> None:
        obj = candidate.InstallationCandidate(
            "A", "1.0.0", Link("https://somewhere.com/path/A-1.0.0.tar.gz")
        )
        assert obj.name == "A"
        assert obj.version == parse_version("1.0.0")
        assert obj.link.url == "https://somewhere.com/path/A-1.0.0.tar.gz"
