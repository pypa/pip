import os
import shutil
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any
from unittest.mock import Mock, patch

import pytest

from pip._vendor.requests import Response

from pip._internal.exceptions import MetadataInvalid, SidecarMetadataInconsistent
from pip._internal.exceptions.hashes import HashMismatch
from pip._internal.metadata import BaseDistribution, get_metadata_distribution
from pip._internal.models.link import Link
from pip._internal.network.download import Downloader
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import (
    _check_sidecar_matches_wheel,
    unpack_url,
)
from pip._internal.utils.hashes import Hashes

from tests.lib import TestData
from tests.lib.requests_mocks import MockResponse


def test_unpack_url_with_urllib_response_without_content_type(data: TestData) -> None:
    """
    It should download and unpack files even if no Content-Type header exists
    """
    _real_session = PipSession()

    def _fake_session_get(*args: Any, **kwargs: Any) -> Response:
        resp = _real_session.get(*args, **kwargs)
        del resp.headers["Content-Type"]
        return resp

    session = Mock()
    session.resume_retries = 0
    session.get = _fake_session_get
    download = Downloader(session, progress_bar="on")

    uri = data.packages.joinpath("simple-1.0.tar.gz").as_uri()
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_url(
            link,
            temp_dir,
            download=download,
            download_dir=None,
            verbosity=0,
        )
        assert set(os.listdir(temp_dir)) == {
            "PKG-INFO",
            "setup.cfg",
            "setup.py",
            "simple",
            "simple.egg-info",
        }
    finally:
        rmtree(temp_dir)


@patch("pip._internal.network.download.raise_for_status")
def test_download_http_url__no_directory_traversal(
    mock_raise_for_status: Mock, tmpdir: Path
) -> None:
    """
    Test that directory traversal doesn't happen on download when the
    Content-Disposition header contains a filename with a ".." path part.
    """
    mock_url = "http://www.example.com/whatever.tgz"
    contents = b"downloaded"
    link = Link(mock_url)

    session = Mock()
    session.resume_retries = 0
    resp = MockResponse(contents)
    resp.url = mock_url
    resp.headers.update(
        {
            # Set the content-type to a random value to prevent
            # mimetypes.guess_extension from guessing the extension.
            "content-type": "random",
            "content-disposition": 'attachment;filename="../out_dir_file"',
        }
    )
    session.get.return_value = resp
    download = Downloader(session, progress_bar="on")

    download_dir = os.fspath(tmpdir.joinpath("download"))
    os.mkdir(download_dir)
    file_path, content_type = download(link, download_dir)
    # The file should be downloaded to download_dir.
    actual = os.listdir(download_dir)
    assert actual == ["out_dir_file"]
    mock_raise_for_status.assert_called_once_with(resp)


@pytest.fixture
def clean_project(tmpdir_factory: pytest.TempPathFactory, data: TestData) -> Path:
    tmpdir = tmpdir_factory.mktemp("clean_project")
    new_project_dir = tmpdir.joinpath("FSPkg")
    path = data.packages.joinpath("FSPkg")
    shutil.copytree(path, new_project_dir)
    return new_project_dir


class Test_unpack_url:
    def prep(self, tmpdir: Path, data: TestData) -> None:
        self.build_dir = os.fspath(tmpdir.joinpath("build"))
        self.download_dir = tmpdir.joinpath("download")
        os.mkdir(self.build_dir)
        os.mkdir(self.download_dir)
        self.dist_file = "simple-1.0.tar.gz"
        self.dist_file2 = "simple-2.0.tar.gz"
        self.dist_path = data.packages.joinpath(self.dist_file)
        self.dist_path2 = data.packages.joinpath(self.dist_file2)
        self.dist_url = Link(self.dist_path.as_uri())
        self.dist_url2 = Link(self.dist_path2.as_uri())
        self.no_download = Mock(side_effect=AssertionError)

    def test_unpack_url_no_download(self, tmpdir: Path, data: TestData) -> None:
        self.prep(tmpdir, data)
        unpack_url(self.dist_url, self.build_dir, self.no_download, verbosity=0)
        assert os.path.isdir(os.path.join(self.build_dir, "simple"))
        assert not os.path.isfile(os.path.join(self.download_dir, self.dist_file))

    def test_unpack_url_bad_hash(self, tmpdir: Path, data: TestData) -> None:
        """
        Test when the file url hash fragment is wrong
        """
        self.prep(tmpdir, data)
        url = f"{self.dist_url.url}#md5=bogus"
        dist_url = Link(url)
        with pytest.raises(HashMismatch):
            unpack_url(
                dist_url,
                self.build_dir,
                download=self.no_download,
                hashes=Hashes({"md5": ["bogus"]}),
                verbosity=0,
            )


def _metadata(*lines: str, name: str = "pkg", version: str = "1.0") -> str:
    metadata = [
        "Metadata-Version: 2.1",
        f"Name: {name}",
        f"Version: {version}",
        *lines,
    ]
    return "\n".join(metadata) + "\n"


def _make_distribution(metadata: str) -> BaseDistribution:
    return get_metadata_distribution(
        metadata.encode("utf-8"),
        "pkg-1.0-py3-none-any.whl",
        "pkg",
    )


class TestCheckSidecarMatchesWheel:
    """Exercise :func:`_check_sidecar_matches_wheel` for each of the
    fields it cross-checks between a PEP 658 sidecar and a downloaded wheel.
    """

    def _req(self) -> Mock:
        # The helper only uses the ``req`` argument to build the resulting
        # exception, so a stand-in object is enough.
        return Mock()

    def test_matching_metadata_does_not_raise(self) -> None:
        dist = _make_distribution(
            _metadata(
                "Requires-Python: >=3.9",
                "Requires-Dist: requests>=2.0",
                "Provides-Extra: extra",
            )
        )
        _check_sidecar_matches_wheel(self._req(), dist, dist)

    def test_requires_dist_canonicalization_is_tolerated(self) -> None:
        sidecar = _make_distribution(_metadata("Requires-Dist: Requests >= 2.0"))
        wheel = _make_distribution(_metadata("Requires-Dist: requests>=2.0"))
        _check_sidecar_matches_wheel(self._req(), sidecar, wheel)

    def test_folded_requires_dist_header_is_tolerated(self) -> None:
        # For a folded Requires-Dist header, the email parser preserves a
        # leading newline in the raw value on Python versions without the
        # python/cpython#124452 fix (3.10, 3.11, <3.12.8, 3.13.0). The check
        # must strip it, like iter_dependencies() does.
        dist = _make_distribution(
            _metadata(
                "Requires-Dist:",
                " some-package-with-a-very-long-name[extra-one]>=2.31.0,<3.0.0",
            )
        )
        _check_sidecar_matches_wheel(self._req(), dist, dist)

    def test_requires_dist_mismatch_raises(self) -> None:
        sidecar = _make_distribution(_metadata("Requires-Dist: shadow-pkg"))
        wheel = _make_distribution(_metadata())
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Requires-Dist"
        assert excinfo.value.f_val == "shadow-pkg"
        assert excinfo.value.m_val == ""

    def test_requires_dist_diff_reports_only_differences(self) -> None:
        sidecar = _make_distribution(
            _metadata(
                "Requires-Dist: shared-a",
                "Requires-Dist: shared-b",
                "Requires-Dist: only-in-sidecar",
            )
        )
        wheel = _make_distribution(
            _metadata(
                "Requires-Dist: shared-a",
                "Requires-Dist: shared-b",
                "Requires-Dist: only-in-wheel",
            )
        )
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Requires-Dist"
        assert excinfo.value.f_val == "only-in-sidecar"
        assert excinfo.value.m_val == "only-in-wheel"

    def test_requires_python_mismatch_raises(self) -> None:
        sidecar = _make_distribution(_metadata("Requires-Python: >=3.9"))
        wheel = _make_distribution(_metadata())
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Requires-Python"
        assert excinfo.value.f_val == ">=3.9"
        assert excinfo.value.m_val == ""

    def test_provides_extra_mismatch_raises(self) -> None:
        sidecar = _make_distribution(_metadata("Provides-Extra: extra"))
        wheel = _make_distribution(_metadata())
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Provides-Extra"
        assert excinfo.value.f_val == "extra"
        assert excinfo.value.m_val == ""

    def test_name_mismatch_raises(self) -> None:
        sidecar = _make_distribution(_metadata(name="other-pkg"))
        wheel = _make_distribution(_metadata(name="pkg"))
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Name"
        assert excinfo.value.f_val == "other-pkg"
        assert excinfo.value.m_val == "pkg"

    def test_name_canonicalization_is_tolerated(self) -> None:
        sidecar = _make_distribution(_metadata(name="Pkg_Name"))
        wheel = _make_distribution(_metadata(name="pkg-name"))
        _check_sidecar_matches_wheel(self._req(), sidecar, wheel)

    def test_version_mismatch_raises(self) -> None:
        sidecar = _make_distribution(_metadata(version="1.0"))
        wheel = _make_distribution(_metadata(version="2.0"))
        with pytest.raises(SidecarMetadataInconsistent) as excinfo:
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
        assert excinfo.value.field == "Version"
        assert excinfo.value.f_val == "1.0"
        assert excinfo.value.m_val == "2.0"

    def test_version_normalization_is_tolerated(self) -> None:
        sidecar = _make_distribution(_metadata(version="1.0"))
        wheel = _make_distribution(_metadata(version="1.0.0"))
        _check_sidecar_matches_wheel(self._req(), sidecar, wheel)

    def test_invalid_requires_dist_raises_metadata_invalid(self) -> None:
        sidecar = _make_distribution(
            _metadata("Requires-Dist: not a valid requirement")
        )
        wheel = _make_distribution(_metadata())
        with pytest.raises(MetadataInvalid):
            _check_sidecar_matches_wheel(self._req(), sidecar, wheel)
