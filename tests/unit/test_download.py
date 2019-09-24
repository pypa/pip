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
from pip._vendor.cachecontrol.caches import FileCache

import pip
from pip._internal.download import (
    CI_ENVIRONMENT_VARIABLES,
    PipSession,
    SafeFileCache,
    _copy_source_tree,
    _download_http_url,
    parse_content_disposition,
    sanitize_content_filename,
    unpack_file_url,
    unpack_http_url,
)
from pip._internal.exceptions import HashMismatch
from pip._internal.models.link import Link
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.urls import path_to_url
from tests.lib import create_file
from tests.lib.filesystem import (
    get_filelist,
    make_socket_file,
    make_unreadable_file,
)
from tests.lib.path import Path


@pytest.fixture(scope="function")
def cache_tmpdir(tmpdir):
    cache_dir = tmpdir.joinpath("cache")
    cache_dir.mkdir(parents=True)
    yield cache_dir


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

    uri = path_to_url(data.packages.joinpath("simple-1.0.tar.gz"))
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_http_url(
            link,
            temp_dir,
            download_dir=None,
            session=session,
        )
        assert set(os.listdir(temp_dir)) == {
            'PKG-INFO', 'setup.cfg', 'setup.py', 'simple', 'simple.egg-info'
        }
    finally:
        rmtree(temp_dir)


def get_user_agent():
    return PipSession().headers["User-Agent"]


def test_user_agent():
    user_agent = get_user_agent()

    assert user_agent.startswith("pip/%s" % pip.__version__)


@pytest.mark.parametrize('name, expected_like_ci', [
    ('BUILD_BUILDID', True),
    ('BUILD_ID', True),
    ('CI', True),
    ('PIP_IS_CI', True),
    # Test a prefix substring of one of the variable names we use.
    ('BUILD', False),
])
def test_user_agent__ci(monkeypatch, name, expected_like_ci):
    # Delete the variable names we use to check for CI to prevent the
    # detection from always returning True in case the tests are being run
    # under actual CI.  It is okay to depend on CI_ENVIRONMENT_VARIABLES
    # here (part of the code under test) because this setup step can only
    # prevent false test failures.  It can't cause a false test passage.
    for ci_name in CI_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(ci_name, raising=False)

    # Confirm the baseline before setting the environment variable.
    user_agent = get_user_agent()
    assert '"ci":null' in user_agent
    assert '"ci":true' not in user_agent

    monkeypatch.setenv(name, 'true')
    user_agent = get_user_agent()
    assert ('"ci":true' in user_agent) == expected_like_ci
    assert ('"ci":null' in user_agent) == (not expected_like_ci)


def test_user_agent_user_data(monkeypatch):
    monkeypatch.setenv("PIP_USER_AGENT_USER_DATA", "some_string")
    assert "some_string" in PipSession().headers["User-Agent"]


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


@patch('pip._internal.download.unpack_file')
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

    download_dir = mkdtemp()
    try:
        downloaded_file = os.path.join(download_dir, 'somepackage.tgz')
        create_file(downloaded_file, 'some contents')

        unpack_http_url(
            link,
            'location',
            download_dir=download_dir,
            session=session,
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

    download_dir = tmpdir.joinpath('download')
    os.mkdir(download_dir)
    file_path, content_type = _download_http_url(
        link,
        session,
        download_dir,
        hashes=None,
        progress_bar='on',
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


class TestSafeFileCache:
    """
    The no_perms test are useless on Windows since SafeFileCache uses
    pip._internal.utils.filesystem.check_path_owner which is based on
    os.geteuid which is absent on Windows.
    """

    def test_cache_roundtrip(self, cache_tmpdir):

        cache = SafeFileCache(cache_tmpdir)
        assert cache.get("test key") is None
        cache.set("test key", b"a test string")
        assert cache.get("test key") == b"a test string"
        cache.delete("test key")
        assert cache.get("test key") is None

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_get_no_perms(self, cache_tmpdir, monkeypatch):
        os.chmod(cache_tmpdir, 000)

        monkeypatch.setattr(os.path, "exists", lambda x: True)

        cache = SafeFileCache(cache_tmpdir)
        cache.get("foo")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_set_no_perms(self, cache_tmpdir):
        os.chmod(cache_tmpdir, 000)

        cache = SafeFileCache(cache_tmpdir)
        cache.set("foo", b"bar")

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_safe_delete_no_perms(self, cache_tmpdir):
        os.chmod(cache_tmpdir, 000)

        cache = SafeFileCache(cache_tmpdir)
        cache.delete("foo")

    def test_cache_hashes_are_same(self, cache_tmpdir):
        cache = SafeFileCache(cache_tmpdir)
        key = "test key"
        fake_cache = Mock(
            FileCache, directory=cache.directory, encode=FileCache.encode
        )
        assert cache._get_cache_path(key) == FileCache._fn(fake_cache, key)


class TestPipSession:

    def test_cache_defaults_off(self):
        session = PipSession()

        assert not hasattr(session.adapters["http://"], "cache")
        assert not hasattr(session.adapters["https://"], "cache")

    def test_cache_is_enabled(self, tmpdir):
        session = PipSession(cache=tmpdir.joinpath("test-cache"))

        assert hasattr(session.adapters["https://"], "cache")

        assert (session.adapters["https://"].cache.directory ==
                tmpdir.joinpath("test-cache"))

    def test_http_cache_is_not_enabled(self, tmpdir):
        session = PipSession(cache=tmpdir.joinpath("test-cache"))

        assert not hasattr(session.adapters["http://"], "cache")

    def test_insecure_host_adapter(self, tmpdir):
        session = PipSession(
            cache=tmpdir.joinpath("test-cache"),
            trusted_hosts=["example.com"],
        )

        assert "https://example.com/" in session.adapters
        # Check that the "port wildcard" is present.
        assert "https://example.com:" in session.adapters
        # Check that the cache isn't enabled.
        assert not hasattr(session.adapters["https://example.com/"], "cache")

    def test_add_trusted_host(self):
        # Leave a gap to test how the ordering is affected.
        trusted_hosts = ['host1', 'host3']
        session = PipSession(trusted_hosts=trusted_hosts)
        insecure_adapter = session._insecure_adapter
        prefix2 = 'https://host2/'
        prefix3 = 'https://host3/'
        prefix3_wildcard = 'https://host3:'

        # Confirm some initial conditions as a baseline.
        assert session.pip_trusted_origins == [
            ('host1', None), ('host3', None)
        ]
        assert session.adapters[prefix3] is insecure_adapter
        assert session.adapters[prefix3_wildcard] is insecure_adapter

        assert prefix2 not in session.adapters

        # Test adding a new host.
        session.add_trusted_host('host2')
        assert session.pip_trusted_origins == [
            ('host1', None), ('host3', None), ('host2', None)
        ]
        # Check that prefix3 is still present.
        assert session.adapters[prefix3] is insecure_adapter
        assert session.adapters[prefix2] is insecure_adapter

        # Test that adding the same host doesn't create a duplicate.
        session.add_trusted_host('host3')
        assert session.pip_trusted_origins == [
            ('host1', None), ('host3', None), ('host2', None)
        ], 'actual: {}'.format(session.pip_trusted_origins)

        session.add_trusted_host('host4:8080')
        prefix4 = 'https://host4:8080/'
        assert session.pip_trusted_origins == [
            ('host1', None), ('host3', None),
            ('host2', None), ('host4', 8080)
        ]
        assert session.adapters[prefix4] is insecure_adapter

    def test_add_trusted_host__logging(self, caplog):
        """
        Test logging when add_trusted_host() is called.
        """
        trusted_hosts = ['host0', 'host1']
        session = PipSession(trusted_hosts=trusted_hosts)
        with caplog.at_level(logging.INFO):
            # Test adding an existing host.
            session.add_trusted_host('host1', source='somewhere')
            session.add_trusted_host('host2')
            # Test calling add_trusted_host() on the same host twice.
            session.add_trusted_host('host2')

        actual = [(r.levelname, r.message) for r in caplog.records]
        # Observe that "host0" isn't included in the logs.
        expected = [
            ('INFO', "adding trusted host: 'host1' (from somewhere)"),
            ('INFO', "adding trusted host: 'host2'"),
            ('INFO', "adding trusted host: 'host2'"),
        ]
        assert actual == expected

    def test_iter_secure_origins(self):
        trusted_hosts = ['host1', 'host2', 'host3:8080']
        session = PipSession(trusted_hosts=trusted_hosts)

        actual = list(session.iter_secure_origins())
        assert len(actual) == 9
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ('https', '*', '*')
        assert actual[-3:] == [
            ('*', 'host1', '*'),
            ('*', 'host2', '*'),
            ('*', 'host3', 8080)
        ]

    def test_iter_secure_origins__trusted_hosts_empty(self):
        """
        Test iter_secure_origins() after passing trusted_hosts=[].
        """
        session = PipSession(trusted_hosts=[])

        actual = list(session.iter_secure_origins())
        assert len(actual) == 6
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ('https', '*', '*')

    @pytest.mark.parametrize(
        'location, trusted, expected',
        [
            ("http://pypi.org/something", [], False),
            ("https://pypi.org/something", [], True),
            ("git+http://pypi.org/something", [], False),
            ("git+https://pypi.org/something", [], True),
            ("git+ssh://git@pypi.org/something", [], True),
            ("http://localhost", [], True),
            ("http://127.0.0.1", [], True),
            ("http://example.com/something/", [], False),
            ("http://example.com/something/", ["example.com"], True),
            # Try changing the case.
            ("http://eXample.com/something/", ["example.cOm"], True),
            # Test hosts with port.
            ("http://example.com:8080/something/", ["example.com"], True),
            # Test a trusted_host with a port.
            ("http://example.com:8080/something/", ["example.com:8080"], True),
            ("http://example.com/something/", ["example.com:8080"], False),
            (
                "http://example.com:8888/something/",
                ["example.com:8080"],
                False
            ),
        ],
    )
    def test_is_secure_origin(self, caplog, location, trusted, expected):
        class MockLogger(object):
            def __init__(self):
                self.called = False

            def warning(self, *args, **kwargs):
                self.called = True

        session = PipSession(trusted_hosts=trusted)
        actual = session.is_secure_origin(location)
        assert actual == expected

        log_records = [(r.levelname, r.message) for r in caplog.records]
        if expected:
            assert not log_records
            return

        assert len(log_records) == 1
        actual_level, actual_message = log_records[0]
        assert actual_level == 'WARNING'
        assert 'is not a trusted or secure host' in actual_message
