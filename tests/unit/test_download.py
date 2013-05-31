import hashlib
import os
from shutil import rmtree
from tempfile import mkdtemp

from mock import patch
import pip
from pip.backwardcompat import urllib, BytesIO, b
from pip.download import (_get_response_from_url as _get_response_from_url_original,
                          path_to_url2, unpack_http_url, URLOpener)
from pip.index import Link
from tests.lib import tests_data


def test_unpack_http_url_with_urllib_response_without_content_type():
    """
    It should download and unpack files even if no Content-Type header exists
    """
    def _get_response_from_url_mock(*args, **kw):
        resp = _get_response_from_url_original(*args, **kw)
        del resp.info()['content-type']
        return resp

    with patch('pip.download._get_response_from_url', _get_response_from_url_mock) as mocked:
        uri = path_to_url2(os.path.join(tests_data, 'packages', 'simple-1.0.tar.gz'))
        link = Link(uri)
        temp_dir = mkdtemp()
        try:
            unpack_http_url(link, temp_dir, download_cache=None, download_dir=None)
            assert set(os.listdir(temp_dir)) == set(['PKG-INFO', 'setup.cfg', 'setup.py', 'simple', 'simple.egg-info'])
        finally:
            rmtree(temp_dir)


def test_user_agent():
    opener = URLOpener().get_opener()
    user_agent = [x for x in opener.addheaders if x[0].lower() == "user-agent"][0]
    assert user_agent[1].startswith("pip/%s" % pip.__version__)


def _write_file(fn, contents):
    with open(fn, 'w') as fh:
        fh.write(contents)


class MockResponse(object):
    def __init__(self, contents):
        self._io = BytesIO(contents)

    def read(self, *a, **kw):
        return self._io.read(*a, **kw)


@patch('pip.download.unpack_file')
@patch('pip.download._get_response_from_url')
def test_unpack_http_url_bad_cache_checksum(mock_get_response, mock_unpack_file):
    """
    If cached download has bad checksum, re-download.
    """
    base_url = 'http://www.example.com/somepackage.tgz'
    contents = b('downloaded')
    download_hash = hashlib.new('sha1', contents)
    link = Link(base_url + '#sha1=' + download_hash.hexdigest())
    response = mock_get_response.return_value = MockResponse(contents)
    response.info = lambda: {'content-type': 'application/x-tar'}
    response.geturl = lambda: base_url

    cache_dir = mkdtemp()
    try:
        cache_file = os.path.join(cache_dir, urllib.quote(base_url, ''))
        cache_ct_file = cache_file + '.content-type'
        _write_file(cache_file, 'some contents')
        _write_file(cache_ct_file, 'application/x-tar')

        unpack_http_url(link, 'location', download_cache=cache_dir)

        # despite existence of cached file with bad hash, downloaded again
        mock_get_response.assert_called_once_with(base_url, link)
        # cached file is replaced with newly downloaded file
        with open(cache_file) as fh:
            assert fh.read() == 'downloaded'

    finally:
        rmtree(cache_dir)


@patch('pip.download.unpack_file')
@patch('pip.download._get_response_from_url')
def test_unpack_http_url_bad_downloaded_checksum(mock_get_response, mock_unpack_file):
    """
    If already-downloaded file has bad checksum, re-download.
    """
    base_url = 'http://www.example.com/somepackage.tgz'
    contents = b('downloaded')
    download_hash = hashlib.new('sha1', contents)
    link = Link(base_url + '#sha1=' + download_hash.hexdigest())
    response = mock_get_response.return_value = MockResponse(contents)
    response.info = lambda: {'content-type': 'application/x-tar'}
    response.geturl = lambda: base_url

    download_dir = mkdtemp()
    try:
        downloaded_file = os.path.join(download_dir, 'somepackage.tgz')
        _write_file(downloaded_file, 'some contents')

        unpack_http_url(link, 'location', download_cache=None, download_dir=download_dir)

        # despite existence of downloaded file with bad hash, downloaded again
        mock_get_response.assert_called_once_with(base_url, link)
        # cached file is replaced with newly downloaded file
        with open(downloaded_file) as fh:
            assert fh.read() == 'downloaded'

    finally:
        rmtree(download_dir)
