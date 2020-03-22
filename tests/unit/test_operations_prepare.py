import os
import shutil
from shutil import rmtree
from tempfile import mkdtemp

import pytest
from mock import Mock

from pip._internal.exceptions import HashMismatch
from pip._internal.models.link import Link
from pip._internal.network.download import Downloader
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import _download_http_url, unpack_url
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.urls import path_to_url
from tests.lib.path import Path
from tests.lib.requests_mocks import MockResponse


def test_unpack_url_with_urllib_response_without_content_type(data):
    """
    It should download and unpack files even if no Content-Type header exists
    """
    _real_session = PipSession()

    def _fake_session_get(*args, **kwargs):
        resp = _real_session.get(*args, **kwargs)
        del resp.headers["Content-Type"]
        return resp

    session = Mock()
    session.get = _fake_session_get
    downloader = Downloader(session, progress_bar="on")

    uri = path_to_url(data.packages.joinpath("simple-1.0.tar.gz"))
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_url(
            link,
            temp_dir,
            downloader=downloader,
            download_dir=None,
        )
        assert set(os.listdir(temp_dir)) == {
            'PKG-INFO', 'setup.cfg', 'setup.py', 'simple', 'simple.egg-info'
        }
    finally:
        rmtree(temp_dir)


def test_download_http_url__no_directory_traversal(tmpdir):
    """
    Test that directory traversal doesn't happen on download when the
    Content-Disposition header contains a filename with a ".." path part.
    """
    mock_url = 'http://www.example.com/whatever.tgz'
    contents = b'downloaded'
    link = Link(mock_url)

    session = Mock()
    resp = MockResponse(contents)
    resp.url = mock_url
    resp.headers = {
        # Set the content-type to a random value to prevent
        # mimetypes.guess_extension from guessing the extension.
        'content-type': 'random',
        'content-disposition': 'attachment;filename="../out_dir_file"'
    }
    session.get.return_value = resp
    downloader = Downloader(session, progress_bar="on")

    download_dir = tmpdir.joinpath('download')
    os.mkdir(download_dir)
    file_path, content_type = _download_http_url(
        link,
        downloader,
        download_dir,
        hashes=None,
    )
    # The file should be downloaded to download_dir.
    actual = os.listdir(download_dir)
    assert actual == ['out_dir_file']


@pytest.fixture
def clean_project(tmpdir_factory, data):
    tmpdir = Path(str(tmpdir_factory.mktemp("clean_project")))
    new_project_dir = tmpdir.joinpath("FSPkg")
    path = data.packages.joinpath("FSPkg")
    shutil.copytree(path, new_project_dir)
    return new_project_dir


class Test_unpack_url(object):

    def prep(self, tmpdir, data):
        self.build_dir = tmpdir.joinpath('build')
        self.download_dir = tmpdir.joinpath('download')
        os.mkdir(self.build_dir)
        os.mkdir(self.download_dir)
        self.dist_file = "simple-1.0.tar.gz"
        self.dist_file2 = "simple-2.0.tar.gz"
        self.dist_path = data.packages.joinpath(self.dist_file)
        self.dist_path2 = data.packages.joinpath(self.dist_file2)
        self.dist_url = Link(path_to_url(self.dist_path))
        self.dist_url2 = Link(path_to_url(self.dist_path2))
        self.no_downloader = Mock(side_effect=AssertionError)

    def test_unpack_url_no_download(self, tmpdir, data):
        self.prep(tmpdir, data)
        unpack_url(self.dist_url, self.build_dir, self.no_downloader)
        assert os.path.isdir(os.path.join(self.build_dir, 'simple'))
        assert not os.path.isfile(
            os.path.join(self.download_dir, self.dist_file))

    def test_unpack_url_bad_hash(self, tmpdir, data,
                                 monkeypatch):
        """
        Test when the file url hash fragment is wrong
        """
        self.prep(tmpdir, data)
        url = '{}#md5=bogus'.format(self.dist_url.url)
        dist_url = Link(url)
        with pytest.raises(HashMismatch):
            unpack_url(dist_url,
                       self.build_dir,
                       downloader=self.no_downloader,
                       hashes=Hashes({'md5': ['bogus']}))

    def test_unpack_url_thats_a_dir(self, tmpdir, data):
        self.prep(tmpdir, data)
        dist_path = data.packages.joinpath("FSPkg")
        dist_url = Link(path_to_url(dist_path))
        unpack_url(dist_url, self.build_dir,
                   downloader=self.no_downloader,
                   download_dir=self.download_dir)
        # test that nothing was copied to build_dir since we build in place
        assert not os.path.exists(os.path.join(self.build_dir, 'fspkg'))
