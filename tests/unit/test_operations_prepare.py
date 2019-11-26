import hashlib
import logging
import os
import shutil
import sys
from io import BytesIO
from shutil import copy, rmtree
from tempfile import mkdtemp

import pytest
from mock import Mock, patch

from pip._internal.exceptions import HashMismatch
from pip._internal.models.link import Link
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import (
    Downloader,
    _copy_source_tree,
    _download_http_url,
    _prepare_download,
    parse_content_disposition,
    sanitize_content_filename,
    unpack_file_url,
    unpack_http_url,
)
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.urls import path_to_url
from tests.lib import create_file
from tests.lib.filesystem import (
    get_filelist,
    make_socket_file,
    make_unreadable_file,
)
from tests.lib.path import Path


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
    downloader = Downloader(session, progress_bar="on")

    uri = path_to_url(data.packages.joinpath("simple-1.0.tar.gz"))
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_http_url(
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


class FakeStream(object):

    def __init__(self, contents):
        self._io = BytesIO(contents)

    def read(self, size, decode_content=None):
        return self._io.read(size)

    def stream(self, size, decode_content=None):
        yield self._io.read(size)

    def release_conn(self):
        pass


class MockResponse(object):

    def __init__(self, contents):
        self.raw = FakeStream(contents)
        self.content = contents
        self.request = None
        self.status_code = 200
        self.connection = None
        self.url = None
        self.headers = {}
        self.history = []

    def raise_for_status(self):
        pass


class MockConnection(object):

    def _send(self, req, **kwargs):
        raise NotImplementedError("_send must be overridden for tests")

    def send(self, req, **kwargs):
        resp = self._send(req, **kwargs)
        for cb in req.hooks.get("response", []):
            cb(resp)
        return resp


class MockRequest(object):

    def __init__(self, url):
        self.url = url
        self.headers = {}
        self.hooks = {}

    def register_hook(self, event_name, callback):
        self.hooks.setdefault(event_name, []).append(callback)


@patch('pip._internal.operations.prepare.unpack_file')
def test_unpack_http_url_bad_downloaded_checksum(mock_unpack_file):
    """
    If already-downloaded file has bad checksum, re-download.
    """
    base_url = 'http://www.example.com/somepackage.tgz'
    contents = b'downloaded'
    download_hash = hashlib.new('sha1', contents)
    link = Link(base_url + '#sha1=' + download_hash.hexdigest())

    session = Mock()
    session.get = Mock()
    response = session.get.return_value = MockResponse(contents)
    response.headers = {'content-type': 'application/x-tar'}
    response.url = base_url
    downloader = Downloader(session, progress_bar="on")

    download_dir = mkdtemp()
    try:
        downloaded_file = os.path.join(download_dir, 'somepackage.tgz')
        create_file(downloaded_file, 'some contents')

        unpack_http_url(
            link,
            'location',
            downloader=downloader,
            download_dir=download_dir,
            hashes=Hashes({'sha1': [download_hash.hexdigest()]})
        )

        # despite existence of downloaded file with bad hash, downloaded again
        session.get.assert_called_once_with(
            'http://www.example.com/somepackage.tgz',
            headers={"Accept-Encoding": "identity"},
            stream=True,
        )
        # cached file is replaced with newly downloaded file
        with open(downloaded_file) as fh:
            assert fh.read() == 'downloaded'

    finally:
        rmtree(download_dir)


@pytest.mark.parametrize("filename, expected", [
    ('dir/file', 'file'),
    ('../file', 'file'),
    ('../../file', 'file'),
    ('../', ''),
    ('../..', '..'),
    ('/', ''),
])
def test_sanitize_content_filename(filename, expected):
    """
    Test inputs where the result is the same for Windows and non-Windows.
    """
    assert sanitize_content_filename(filename) == expected


@pytest.mark.parametrize("filename, win_expected, non_win_expected", [
    ('dir\\file', 'file', 'dir\\file'),
    ('..\\file', 'file', '..\\file'),
    ('..\\..\\file', 'file', '..\\..\\file'),
    ('..\\', '', '..\\'),
    ('..\\..', '..', '..\\..'),
    ('\\', '', '\\'),
])
def test_sanitize_content_filename__platform_dependent(
    filename,
    win_expected,
    non_win_expected
):
    """
    Test inputs where the result is different for Windows and non-Windows.
    """
    if sys.platform == 'win32':
        expected = win_expected
    else:
        expected = non_win_expected
    assert sanitize_content_filename(filename) == expected


@pytest.mark.parametrize("content_disposition, default_filename, expected", [
    ('attachment;filename="../file"', 'df', 'file'),
])
def test_parse_content_disposition(
    content_disposition,
    default_filename,
    expected
):
    actual = parse_content_disposition(content_disposition, default_filename)
    assert actual == expected


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


@pytest.mark.parametrize("url, headers, from_cache, expected", [
    ('http://example.com/foo.tgz', {}, False,
        "Downloading http://example.com/foo.tgz"),
    ('http://example.com/foo.tgz', {'content-length': 2}, False,
        "Downloading http://example.com/foo.tgz (2 bytes)"),
    ('http://example.com/foo.tgz', {'content-length': 2}, True,
        "Using cached http://example.com/foo.tgz (2 bytes)"),
    ('https://files.pythonhosted.org/foo.tgz', {}, False,
        "Downloading foo.tgz"),
    ('https://files.pythonhosted.org/foo.tgz', {'content-length': 2}, False,
        "Downloading foo.tgz (2 bytes)"),
    ('https://files.pythonhosted.org/foo.tgz', {'content-length': 2}, True,
        "Using cached foo.tgz"),
])
def test_prepare_download__log(caplog, url, headers, from_cache, expected):
    caplog.set_level(logging.INFO)
    resp = MockResponse(b'')
    resp.url = url
    resp.headers = headers
    if from_cache:
        resp.from_cache = from_cache
    link = Link(url)
    _prepare_download(resp, link, progress_bar="on")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'INFO'
    assert expected in record.message


@pytest.fixture
def clean_project(tmpdir_factory, data):
    tmpdir = Path(str(tmpdir_factory.mktemp("clean_project")))
    new_project_dir = tmpdir.joinpath("FSPkg")
    path = data.packages.joinpath("FSPkg")
    shutil.copytree(path, new_project_dir)
    return new_project_dir


def test_copy_source_tree(clean_project, tmpdir):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    assert len(expected_files) == 3

    _copy_source_tree(clean_project, target)

    copied_files = get_filelist(target)
    assert expected_files == copied_files


@pytest.mark.skipif("sys.platform == 'win32' or sys.version_info < (3,)")
def test_copy_source_tree_with_socket(clean_project, tmpdir, caplog):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    socket_path = str(clean_project.joinpath("aaa"))
    make_socket_file(socket_path)

    _copy_source_tree(clean_project, target)

    copied_files = get_filelist(target)
    assert expected_files == copied_files

    # Warning should have been logged.
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'WARNING'
    assert socket_path in record.message


@pytest.mark.skipif("sys.platform == 'win32' or sys.version_info < (3,)")
def test_copy_source_tree_with_socket_fails_with_no_socket_error(
    clean_project, tmpdir
):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    make_socket_file(clean_project.joinpath("aaa"))
    unreadable_file = clean_project.joinpath("bbb")
    make_unreadable_file(unreadable_file)

    with pytest.raises(shutil.Error) as e:
        _copy_source_tree(clean_project, target)

    errored_files = [err[0] for err in e.value.args[0]]
    assert len(errored_files) == 1
    assert unreadable_file in errored_files

    copied_files = get_filelist(target)
    # All files without errors should have been copied.
    assert expected_files == copied_files


def test_copy_source_tree_with_unreadable_dir_fails(clean_project, tmpdir):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    unreadable_file = clean_project.joinpath("bbb")
    make_unreadable_file(unreadable_file)

    with pytest.raises(shutil.Error) as e:
        _copy_source_tree(clean_project, target)

    errored_files = [err[0] for err in e.value.args[0]]
    assert len(errored_files) == 1
    assert unreadable_file in errored_files

    copied_files = get_filelist(target)
    # All files without errors should have been copied.
    assert expected_files == copied_files


class Test_unpack_file_url(object):

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
        with open(self.dist_path2, 'rb') as f:
            dist_path2_md5 = hashlib.md5(f.read()).hexdigest()

        unpack_file_url(self.dist_url, self.build_dir,
                        download_dir=self.download_dir)
        # our hash should be the same, i.e. not overwritten by simple-1.0 hash
        with open(dest_file, 'rb') as f:
            assert dist_path2_md5 == hashlib.md5(f.read()).hexdigest()

    def test_unpack_file_url_bad_hash(self, tmpdir, data,
                                      monkeypatch):
        """
        Test when the file url hash fragment is wrong
        """
        self.prep(tmpdir, data)
        url = '{}#md5=bogus'.format(self.dist_url.url)
        dist_url = Link(url)
        with pytest.raises(HashMismatch):
            unpack_file_url(dist_url,
                            self.build_dir,
                            hashes=Hashes({'md5': ['bogus']}))

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

        with open(self.dist_path, 'rb') as f:
            dist_path_md5 = hashlib.md5(f.read()).hexdigest()
        with open(dest_file, 'rb') as f:
            dist_path2_md5 = hashlib.md5(f.read()).hexdigest()

        assert dist_path_md5 != dist_path2_md5

        url = '{}#md5={}'.format(self.dist_url.url, dist_path_md5)
        dist_url = Link(url)
        unpack_file_url(dist_url, self.build_dir,
                        download_dir=self.download_dir,
                        hashes=Hashes({'md5': [dist_path_md5]}))

        # confirm hash is for simple1-1.0
        # the previous bad download has been removed
        with open(dest_file, 'rb') as f:
            assert hashlib.md5(f.read()).hexdigest() == dist_path_md5

    def test_unpack_file_url_thats_a_dir(self, tmpdir, data):
        self.prep(tmpdir, data)
        dist_path = data.packages.joinpath("FSPkg")
        dist_url = Link(path_to_url(dist_path))
        unpack_file_url(dist_url, self.build_dir,
                        download_dir=self.download_dir)
        assert os.path.isdir(os.path.join(self.build_dir, 'fspkg'))


@pytest.mark.parametrize('exclude_dir', [
    '.nox',
    '.tox'
])
def test_unpack_file_url_excludes_expected_dirs(tmpdir, exclude_dir):
    src_dir = tmpdir / 'src'
    dst_dir = tmpdir / 'dst'
    src_included_file = src_dir.joinpath('file.txt')
    src_excluded_dir = src_dir.joinpath(exclude_dir)
    src_excluded_file = src_dir.joinpath(exclude_dir, 'file.txt')
    src_included_dir = src_dir.joinpath('subdir', exclude_dir)

    # set up source directory
    src_excluded_dir.mkdir(parents=True)
    src_included_dir.mkdir(parents=True)
    src_included_file.touch()
    src_excluded_file.touch()

    dst_included_file = dst_dir.joinpath('file.txt')
    dst_excluded_dir = dst_dir.joinpath(exclude_dir)
    dst_excluded_file = dst_dir.joinpath(exclude_dir, 'file.txt')
    dst_included_dir = dst_dir.joinpath('subdir', exclude_dir)

    src_link = Link(path_to_url(src_dir))
    unpack_file_url(
        src_link,
        dst_dir,
        download_dir=None
    )
    assert not os.path.isdir(dst_excluded_dir)
    assert not os.path.isfile(dst_excluded_file)
    assert os.path.isfile(dst_included_file)
    assert os.path.isdir(dst_included_dir)
