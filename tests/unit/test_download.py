import hashlib
import os
from shutil import rmtree, copy
from tempfile import mkdtemp

from mock import Mock, patch
import pytest

import pip
from pip.backwardcompat import urllib, BytesIO, b, pathname2url
from pip.exceptions import HashMismatch
from pip.download import (PipSession, path_to_url, unpack_http_url,
                          url_to_path, unpack_file_url)
from pip.index import Link


def test_unpack_http_url_with_urllib_response_without_content_type(data):
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

    uri = path_to_url(data.packages.join("simple-1.0.tar.gz"))
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_http_url(link, temp_dir,
            download_cache=None,
            download_dir=None,
            session=session,
        )
        assert set(os.listdir(temp_dir)) == set(['PKG-INFO', 'setup.cfg', 'setup.py', 'simple', 'simple.egg-info'])
    finally:
        rmtree(temp_dir)


def test_user_agent():
    PipSession().headers["User-Agent"].startswith("pip/%s" % pip.__version__)


def _write_file(fn, contents):
    with open(fn, 'w') as fh:
        fh.write(contents)


class FakeStream(object):

    def __init__(self, contents):
        self._io = BytesIO(contents)

    def read(self, size, decode_content=None):
        return self._io.read(size)

    def stream(self, size, decode_content=None):
        yield self._io.read(size)


class MockResponse(object):

    def __init__(self, contents):
        self.raw = FakeStream(contents)

    def raise_for_status(self):
        pass


@patch('pip.download.unpack_file')
def test_unpack_http_url_bad_cache_checksum(mock_unpack_file):
    """
    If cached download has bad checksum, re-download.
    """
    base_url = 'http://www.example.com/somepackage.tgz'
    contents = b('downloaded')
    download_hash = hashlib.new('sha1', contents)
    link = Link(base_url + '#sha1=' + download_hash.hexdigest())

    session = Mock()
    session.get = Mock()
    response = session.get.return_value = MockResponse(contents)
    response.headers = {'content-type': 'application/x-tar'}
    response.url = base_url

    cache_dir = mkdtemp()
    try:
        cache_file = os.path.join(cache_dir, urllib.quote(base_url, ''))
        cache_ct_file = cache_file + '.content-type'
        _write_file(cache_file, 'some contents')
        _write_file(cache_ct_file, 'application/x-tar')

        unpack_http_url(link, 'location',
            download_cache=cache_dir,
            session=session,
        )

        # despite existence of cached file with bad hash, downloaded again
        session.get.assert_called_once_with(
            "http://www.example.com/somepackage.tgz",
            stream=True,
        )
        # cached file is replaced with newly downloaded file
        with open(cache_file) as fh:
            assert fh.read() == 'downloaded'

    finally:
        rmtree(cache_dir)


@patch('pip.download.unpack_file')
def test_unpack_http_url_bad_downloaded_checksum(mock_unpack_file):
    """
    If already-downloaded file has bad checksum, re-download.
    """
    base_url = 'http://www.example.com/somepackage.tgz'
    contents = b('downloaded')
    download_hash = hashlib.new('sha1', contents)
    link = Link(base_url + '#sha1=' + download_hash.hexdigest())

    session = Mock()
    session.get = Mock()
    response = session.get.return_value = MockResponse(contents)
    response.headers = {'content-type': 'application/x-tar'}
    response.url = base_url

    download_dir = mkdtemp()
    try:
        downloaded_file = os.path.join(download_dir, 'somepackage.tgz')
        _write_file(downloaded_file, 'some contents')

        unpack_http_url(link, 'location',
            download_cache=None,
            download_dir=download_dir,
            session=session,
        )

        # despite existence of downloaded file with bad hash, downloaded again
        session.get.assert_called_once_with(
            'http://www.example.com/somepackage.tgz',
            stream=True,
        )
        # cached file is replaced with newly downloaded file
        with open(downloaded_file) as fh:
            assert fh.read() == 'downloaded'

    finally:
        rmtree(download_dir)


@pytest.mark.skipif("sys.platform == 'win32'")
def test_path_to_url_unix():
    assert path_to_url('/tmp/file') == 'file:///tmp/file'
    path = os.path.join(os.getcwd(), 'file')
    assert path_to_url('file') == 'file://' + pathname2url(path)


@pytest.mark.skipif("sys.platform == 'win32'")
def test_url_to_path_unix():
    assert url_to_path('file:///tmp/file') == '/tmp/file'


@pytest.mark.skipif("sys.platform != 'win32'")
def test_path_to_url_win():
    assert path_to_url('c:/tmp/file') == 'file:///c:/tmp/file'
    assert path_to_url('c:\\tmp\\file') == 'file:///c:/tmp/file'
    path = os.path.join(os.getcwd(), 'file')
    assert path_to_url('file') == 'file:' + pathname2url(path)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_url_to_path_win():
    assert url_to_path('file:///c:/tmp/file') == 'c:/tmp/file'


class Test_unpack_file_url(object):

    def prep(self, tmpdir, data):
        self.build_dir = tmpdir.join('build')
        self.download_dir = tmpdir.join('download')
        os.mkdir(self.build_dir)
        os.mkdir(self.download_dir)
        self.dist_file = "simple-1.0.tar.gz"
        self.dist_file2 = "simple-2.0.tar.gz"
        self.dist_path = data.packages.join(self.dist_file)
        self.dist_path2 = data.packages.join(self.dist_file2)
        self.dist_url = Link(path_to_url(self.dist_path))
        self.dist_url2 = Link(path_to_url(self.dist_path2))

    def test_unpack_file_url_no_download(self, tmpdir, data):
        self.prep(tmpdir, data)
        unpack_file_url(self.dist_url, self.build_dir)
        assert os.path.isdir(os.path.join(self.build_dir, 'simple'))
        assert not os.path.isfile(
            os.path.join(self.download_dir, self.dist_file))

    def test_unpack_file_url_and_download(self, tmpdir, data):
        self.prep(tmpdir, data)
        unpack_file_url(self.dist_url, self.build_dir,
                        download_dir=self.download_dir)
        assert os.path.isdir(os.path.join(self.build_dir, 'simple'))
        assert os.path.isfile(os.path.join(self.download_dir, self.dist_file))

    def test_unpack_file_url_download_already_exists(self, tmpdir,
                                                     data, monkeypatch):
        self.prep(tmpdir, data)
        # add in previous download (copy simple-2.0 as simple-1.0)
        # so we can tell it didn't get overwritten
        dest_file = os.path.join(self.download_dir, self.dist_file)
        copy(self.dist_path2, dest_file)
        dist_path2_md5 = hashlib.md5(
            open(self.dist_path2, 'rb').read()).hexdigest()

        unpack_file_url(self.dist_url, self.build_dir,
                        download_dir=self.download_dir)
        # our hash should be the same, i.e. not overwritten by simple-1.0 hash
        assert dist_path2_md5 == hashlib.md5(
            open(dest_file, 'rb').read()).hexdigest()

    def test_unpack_file_url_bad_hash(self, tmpdir, data,
                                      monkeypatch):
        """
        Test when the file url hash fragment is wrong
        """
        self.prep(tmpdir, data)
        self.dist_url.url = "%s#md5=bogus" % self.dist_url.url
        with pytest.raises(HashMismatch):
            unpack_file_url(self.dist_url, self.build_dir)

    def test_unpack_file_url_download_bad_hash(self, tmpdir, data,
                                               monkeypatch):
        """
        Test when existing download has different hash from the file url
        fragment
        """
        self.prep(tmpdir, data)

        # add in previous download (copy simple-2.0 as simple-1.0 so it's wrong
        # hash)
        dest_file = os.path.join(self.download_dir, self.dist_file)
        copy(self.dist_path2, dest_file)

        dist_path_md5 = hashlib.md5(
            open(self.dist_path, 'rb').read()).hexdigest()
        dist_path2_md5 = hashlib.md5(open(dest_file, 'rb').read()).hexdigest()

        assert dist_path_md5 != dist_path2_md5

        self.dist_url.url = "%s#md5=%s" % (
            self.dist_url.url,
            dist_path_md5
            )
        unpack_file_url(self.dist_url, self.build_dir,
                        download_dir=self.download_dir)

        # confirm hash is for simple1-1.0
        # the previous bad download has been removed
        assert (hashlib.md5(open(dest_file, 'rb').read()).hexdigest()
                ==
                dist_path_md5
                ), hashlib.md5(open(dest_file, 'rb').read()).hexdigest()

    def test_unpack_file_url_thats_a_dir(self, tmpdir, data):
        self.prep(tmpdir, data)
        dist_path = data.packages.join("FSPkg")
        dist_url = Link(path_to_url(dist_path))
        unpack_file_url(dist_url, self.build_dir,
                        download_dir=self.download_dir)
        assert os.path.isdir(os.path.join(self.build_dir, 'fspkg'))
