import functools
import hashlib
import os
import sys
from io import BytesIO
from shutil import copy, rmtree
from tempfile import mkdtemp

import pytest
from mock import Mock, patch

import pip
from pip._internal.download import (
    CI_ENVIRONMENT_VARIABLES, MultiDomainBasicAuth, PipSession, SafeFileCache,
    _download_http_url, parse_content_disposition, sanitize_content_filename,
    unpack_file_url, unpack_http_url, url_to_path,
)
from pip._internal.exceptions import HashMismatch
from pip._internal.models.link import Link
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.misc import path_to_url
from tests.lib import create_file


@pytest.fixture(scope="function")
def cache_tmpdir(tmpdir):
    cache_dir = tmpdir.join("cache")
    cache_dir.makedirs()
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

    uri = path_to_url(data.packages.join("simple-1.0.tar.gz"))
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

    download_dir = tmpdir.join('download')
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


@pytest.mark.parametrize("url,win_expected,non_win_expected", [
    ('file:tmp', 'tmp', 'tmp'),
    ('file:c:/path/to/file', r'C:\path\to\file', 'c:/path/to/file'),
    ('file:/path/to/file', r'\path\to\file', '/path/to/file'),
    ('file://localhost/tmp/file', r'\tmp\file', '/tmp/file'),
    ('file://localhost/c:/tmp/file', r'C:\tmp\file', '/c:/tmp/file'),
    ('file://somehost/tmp/file', r'\\somehost\tmp\file', None),
    ('file:///tmp/file', r'\tmp\file', '/tmp/file'),
    ('file:///c:/tmp/file', r'C:\tmp\file', '/c:/tmp/file'),
])
def test_url_to_path(url, win_expected, non_win_expected):
    if sys.platform == 'win32':
        expected_path = win_expected
    else:
        expected_path = non_win_expected

    if expected_path is None:
        with pytest.raises(ValueError):
            url_to_path(url)
    else:
        assert url_to_path(url) == expected_path


@pytest.mark.skipif("sys.platform != 'win32'")
def test_url_to_path_path_to_url_symmetry_win():
    path = r'C:\tmp\file'
    assert url_to_path(path_to_url(path)) == path

    unc_path = r'\\unc\share\path'
    assert url_to_path(path_to_url(unc_path)) == unc_path


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
        self.dist_url.url = "%s#md5=bogus" % self.dist_url.url
        with pytest.raises(HashMismatch):
            unpack_file_url(self.dist_url,
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

        self.dist_url.url = "%s#md5=%s" % (
            self.dist_url.url,
            dist_path_md5
        )
        unpack_file_url(self.dist_url, self.build_dir,
                        download_dir=self.download_dir,
                        hashes=Hashes({'md5': [dist_path_md5]}))

        # confirm hash is for simple1-1.0
        # the previous bad download has been removed
        with open(dest_file, 'rb') as f:
            assert hashlib.md5(f.read()).hexdigest() == dist_path_md5

    def test_unpack_file_url_thats_a_dir(self, tmpdir, data):
        self.prep(tmpdir, data)
        dist_path = data.packages.join("FSPkg")
        dist_url = Link(path_to_url(dist_path))
        unpack_file_url(dist_url, self.build_dir,
                        download_dir=self.download_dir)
        assert os.path.isdir(os.path.join(self.build_dir, 'fspkg'))


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


class TestPipSession:

    def test_cache_defaults_off(self):
        session = PipSession()

        assert not hasattr(session.adapters["http://"], "cache")
        assert not hasattr(session.adapters["https://"], "cache")

    def test_cache_is_enabled(self, tmpdir):
        session = PipSession(cache=tmpdir.join("test-cache"))

        assert hasattr(session.adapters["https://"], "cache")

        assert (session.adapters["https://"].cache.directory ==
                tmpdir.join("test-cache"))

    def test_http_cache_is_not_enabled(self, tmpdir):
        session = PipSession(cache=tmpdir.join("test-cache"))

        assert not hasattr(session.adapters["http://"], "cache")

    def test_insecure_host_cache_is_not_enabled(self, tmpdir):
        session = PipSession(
            cache=tmpdir.join("test-cache"),
            insecure_hosts=["example.com"],
        )

        assert not hasattr(session.adapters["https://example.com/"], "cache")


def test_get_credentials():
    auth = MultiDomainBasicAuth()
    get = auth._get_url_and_credentials

    # Check URL parsing
    assert get("http://foo:bar@example.com/path") \
        == ('http://example.com/path', 'foo', 'bar')
    assert auth.passwords['example.com'] == ('foo', 'bar')

    auth.passwords['example.com'] = ('user', 'pass')
    assert get("http://foo:bar@example.com/path") \
        == ('http://example.com/path', 'user', 'pass')


def test_get_index_url_credentials():
    auth = MultiDomainBasicAuth(index_urls=[
        "http://foo:bar@example.com/path"
    ])
    get = functools.partial(
        auth._get_new_credentials,
        allow_netrc=False,
        allow_keyring=False
    )

    # Check resolution of indexes
    assert get("http://example.com/path/path2") == ('foo', 'bar')
    assert get("http://example.com/path3/path2") == (None, None)


class KeyringModuleV1(object):
    """Represents the supported API of keyring before get_credential
    was added.
    """

    def __init__(self):
        self.saved_passwords = []

    def get_password(self, system, username):
        if system == "example.com" and username:
            return username + "!netloc"
        if system == "http://example.com/path2" and username:
            return username + "!url"
        return None

    def set_password(self, system, username, password):
        self.saved_passwords.append((system, username, password))


@pytest.mark.parametrize('url, expect', (
    ("http://example.com/path1", (None, None)),
    # path1 URLs will be resolved by netloc
    ("http://user@example.com/path1", ("user", "user!netloc")),
    ("http://user2@example.com/path1", ("user2", "user2!netloc")),
    # path2 URLs will be resolved by index URL
    ("http://example.com/path2/path3", (None, None)),
    ("http://foo@example.com/path2/path3", ("foo", "foo!url")),
))
def test_keyring_get_password(monkeypatch, url, expect):
    monkeypatch.setattr('pip._internal.download.keyring', KeyringModuleV1())
    auth = MultiDomainBasicAuth(index_urls=["http://example.com/path2"])

    actual = auth._get_new_credentials(url, allow_netrc=False,
                                       allow_keyring=True)
    assert actual == expect


def test_keyring_get_password_after_prompt(monkeypatch):
    monkeypatch.setattr('pip._internal.download.keyring', KeyringModuleV1())
    auth = MultiDomainBasicAuth()

    def ask_input(prompt):
        assert prompt == "User for example.com: "
        return "user"

    monkeypatch.setattr('pip._internal.download.ask_input', ask_input)
    actual = auth._prompt_for_password("example.com")
    assert actual == ("user", "user!netloc", False)


def test_keyring_get_password_username_in_index(monkeypatch):
    monkeypatch.setattr('pip._internal.download.keyring', KeyringModuleV1())
    auth = MultiDomainBasicAuth(index_urls=["http://user@example.com/path2"])
    get = functools.partial(
        auth._get_new_credentials,
        allow_netrc=False,
        allow_keyring=True
    )

    assert get("http://example.com/path2/path3") == ("user", "user!url")
    assert get("http://example.com/path4/path1") == (None, None)


@pytest.mark.parametrize("response_status, creds, expect_save", (
    (403, ("user", "pass", True), False),
    (200, ("user", "pass", True), True,),
    (200, ("user", "pass", False), False,),
))
def test_keyring_set_password(monkeypatch, response_status, creds,
                              expect_save):
    keyring = KeyringModuleV1()
    monkeypatch.setattr('pip._internal.download.keyring', keyring)
    auth = MultiDomainBasicAuth(prompting=True)
    monkeypatch.setattr(auth, '_get_url_and_credentials',
                        lambda u: (u, None, None))
    monkeypatch.setattr(auth, '_prompt_for_password', lambda *a: creds)
    if creds[2]:
        # when _prompt_for_password indicates to save, we should save
        def should_save_password_to_keyring(*a):
            return True
    else:
        # when _prompt_for_password indicates not to save, we should
        # never call this function
        def should_save_password_to_keyring(*a):
            assert False, ("_should_save_password_to_keyring should not be " +
                           "called")
    monkeypatch.setattr(auth, '_should_save_password_to_keyring',
                        should_save_password_to_keyring)

    req = MockRequest("https://example.com")
    resp = MockResponse(b"")
    resp.url = req.url
    connection = MockConnection()

    def _send(sent_req, **kwargs):
        assert sent_req is req
        assert "Authorization" in sent_req.headers
        r = MockResponse(b"")
        r.status_code = response_status
        return r

    connection._send = _send

    resp.request = req
    resp.status_code = 401
    resp.connection = connection

    auth.handle_401(resp)

    if expect_save:
        assert keyring.saved_passwords == [("example.com", creds[0], creds[1])]
    else:
        assert keyring.saved_passwords == []


class KeyringModuleV2(object):
    """Represents the current supported API of keyring"""

    class Credential(object):
        def __init__(self, username, password):
            self.username = username
            self.password = password

    def get_password(self, system, username):
        assert False, "get_password should not ever be called"

    def get_credential(self, system, username):
        if system == "http://example.com/path2":
            return self.Credential("username", "url")
        if system == "example.com":
            return self.Credential("username", "netloc")
        return None


@pytest.mark.parametrize('url, expect', (
    ("http://example.com/path1", ("username", "netloc")),
    ("http://example.com/path2/path3", ("username", "url")),
    ("http://user2@example.com/path2/path3", ("username", "url")),
))
def test_keyring_get_credential(monkeypatch, url, expect):
    monkeypatch.setattr(pip._internal.download, 'keyring', KeyringModuleV2())
    auth = MultiDomainBasicAuth(index_urls=["http://example.com/path2"])

    assert auth._get_new_credentials(url, allow_netrc=False,
                                     allow_keyring=True) \
        == expect
