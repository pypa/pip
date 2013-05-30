import os
from shutil import rmtree
from tempfile import mkdtemp

import pip
from mock import patch
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


def test_bad_cache_checksum():
    """
    If cached download has bad checksum, re-download.
    """


def test_bad_already_downloaded_checksum():
    """
    If already-downloaded file has bad checksum, re-download.
    """
