import functools

import pytest

import pip._internal.network.auth
from pip._internal.network.auth import MultiDomainBasicAuth
from tests.lib.requests_mocks import MockConnection, MockRequest, MockResponse


@pytest.mark.parametrize(
    ["input_url", "url", "username", "password"],
    [
        (
            "http://user%40email.com:password@example.com/path",
            "http://example.com/path",
            "user@email.com",
            "password",
        ),
        (
            "http://username:password@example.com/path",
            "http://example.com/path",
            "username",
            "password",
        ),
        (
            "http://token@example.com/path",
            "http://example.com/path",
            "token",
            "",
        ),
        (
            "http://example.com/path",
            "http://example.com/path",
            None,
            None,
        ),
    ],
)
def test_get_credentials_parses_correctly(input_url, url, username, password):
    auth = MultiDomainBasicAuth()
    get = auth._get_url_and_credentials

    # Check URL parsing
    assert get(input_url) == (url, username, password)
    assert (
        # There are no credentials in the URL
        (username is None and password is None)
        or
        # Credentials were found and "cached" appropriately
        auth.passwords["example.com"] == (username, password)
    )


def test_get_credentials_not_to_uses_cached_credentials():
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://foo:bar@example.com/path")
    expected = ("http://example.com/path", "foo", "bar")
    assert got == expected


def test_get_credentials_not_to_uses_cached_credentials_only_username():
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://foo@example.com/path")
    expected = ("http://example.com/path", "foo", "")
    assert got == expected


def test_get_credentials_uses_cached_credentials():
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://example.com/path")
    expected = ("http://example.com/path", "user", "pass")
    assert got == expected


def test_get_index_url_credentials():
    auth = MultiDomainBasicAuth(index_urls=["http://foo:bar@example.com/path"])
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=False
    )

    # Check resolution of indexes
    assert get("http://example.com/path/path2") == ("foo", "bar")
    assert get("http://example.com/path3/path2") == (None, None)


class KeyringModuleV1:
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


@pytest.mark.parametrize(
    "url, expect",
    (
        ("http://example.com/path1", (None, None)),
        # path1 URLs will be resolved by netloc
        ("http://user@example.com/path1", ("user", "user!netloc")),
        ("http://user2@example.com/path1", ("user2", "user2!netloc")),
        # path2 URLs will be resolved by index URL
        ("http://example.com/path2/path3", (None, None)),
        ("http://foo@example.com/path2/path3", ("foo", "foo!url")),
    ),
)
def test_keyring_get_password(monkeypatch, url, expect):
    keyring = KeyringModuleV1()
    monkeypatch.setattr("pip._internal.network.auth.keyring", keyring)
    auth = MultiDomainBasicAuth(index_urls=["http://example.com/path2"])

    actual = auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True)
    assert actual == expect


def test_keyring_get_password_after_prompt(monkeypatch):
    keyring = KeyringModuleV1()
    monkeypatch.setattr("pip._internal.network.auth.keyring", keyring)
    auth = MultiDomainBasicAuth()

    def ask_input(prompt):
        assert prompt == "User for example.com: "
        return "user"

    monkeypatch.setattr("pip._internal.network.auth.ask_input", ask_input)
    actual = auth._prompt_for_password("example.com")
    assert actual == ("user", "user!netloc", False)


def test_keyring_get_password_after_prompt_when_none(monkeypatch):
    keyring = KeyringModuleV1()
    monkeypatch.setattr("pip._internal.network.auth.keyring", keyring)
    auth = MultiDomainBasicAuth()

    def ask_input(prompt):
        assert prompt == "User for unknown.com: "
        return "user"

    def ask_password(prompt):
        assert prompt == "Password: "
        return "fake_password"

    monkeypatch.setattr("pip._internal.network.auth.ask_input", ask_input)
    monkeypatch.setattr("pip._internal.network.auth.ask_password", ask_password)
    actual = auth._prompt_for_password("unknown.com")
    assert actual == ("user", "fake_password", True)


def test_keyring_get_password_username_in_index(monkeypatch):
    keyring = KeyringModuleV1()
    monkeypatch.setattr("pip._internal.network.auth.keyring", keyring)
    auth = MultiDomainBasicAuth(index_urls=["http://user@example.com/path2"])
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=True
    )

    assert get("http://example.com/path2/path3") == ("user", "user!url")
    assert get("http://example.com/path4/path1") == (None, None)


@pytest.mark.parametrize(
    "response_status, creds, expect_save",
    (
        (403, ("user", "pass", True), False),
        (
            200,
            ("user", "pass", True),
            True,
        ),
        (
            200,
            ("user", "pass", False),
            False,
        ),
    ),
)
def test_keyring_set_password(monkeypatch, response_status, creds, expect_save):
    keyring = KeyringModuleV1()
    monkeypatch.setattr("pip._internal.network.auth.keyring", keyring)
    auth = MultiDomainBasicAuth(prompting=True)
    monkeypatch.setattr(auth, "_get_url_and_credentials", lambda u: (u, None, None))
    monkeypatch.setattr(auth, "_prompt_for_password", lambda *a: creds)
    if creds[2]:
        # when _prompt_for_password indicates to save, we should save
        def should_save_password_to_keyring(*a):
            return True

    else:
        # when _prompt_for_password indicates not to save, we should
        # never call this function
        def should_save_password_to_keyring(*a):
            assert False, "_should_save_password_to_keyring should not be called"

    monkeypatch.setattr(
        auth, "_should_save_password_to_keyring", should_save_password_to_keyring
    )

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


class KeyringModuleV2:
    """Represents the current supported API of keyring"""

    class Credential:
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


@pytest.mark.parametrize(
    "url, expect",
    (
        ("http://example.com/path1", ("username", "netloc")),
        ("http://example.com/path2/path3", ("username", "url")),
        ("http://user2@example.com/path2/path3", ("username", "url")),
    ),
)
def test_keyring_get_credential(monkeypatch, url, expect):
    monkeypatch.setattr(pip._internal.network.auth, "keyring", KeyringModuleV2())
    auth = MultiDomainBasicAuth(index_urls=["http://example.com/path2"])

    assert (
        auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True) == expect
    )


class KeyringModuleBroken:
    """Represents the current supported API of keyring, but broken"""

    def __init__(self):
        self._call_count = 0

    def get_credential(self, system, username):
        self._call_count += 1
        raise Exception("This keyring is broken!")


def test_broken_keyring_disables_keyring(monkeypatch):
    keyring_broken = KeyringModuleBroken()
    monkeypatch.setattr(pip._internal.network.auth, "keyring", keyring_broken)

    auth = MultiDomainBasicAuth(index_urls=["http://example.com/"])

    assert keyring_broken._call_count == 0
    for i in range(5):
        url = "http://example.com/path" + str(i)
        assert auth._get_new_credentials(
            url, allow_netrc=False, allow_keyring=True
        ) == (None, None)
        assert keyring_broken._call_count == 1
