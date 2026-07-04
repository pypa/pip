from __future__ import annotations

import functools
import os
import subprocess
import sys
from collections.abc import Iterable
from typing import Any

import pytest

import pip._internal.network.auth
from pip._internal.network.auth import MultiDomainBasicAuth

from tests.lib.requests_mocks import MockConnection, MockRequest, MockResponse


@pytest.fixture(autouse=True)
def reset_keyring() -> Iterable[None]:
    yield None
    # Reset the state of the module between tests
    pip._internal.network.auth.KEYRING_DISABLED = False
    pip._internal.network.auth.get_keyring_provider.cache_clear()


@pytest.mark.parametrize(
    "input_url, url, username, password",
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
def test_get_credentials_parses_correctly(
    input_url: str, url: str, username: str | None, password: str | None
) -> None:
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


def test_get_credentials_not_to_uses_cached_credentials() -> None:
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://foo:bar@example.com/path")
    expected = ("http://example.com/path", "foo", "bar")
    assert got == expected


def test_get_credentials_not_to_uses_cached_credentials_only_username() -> None:
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://foo@example.com/path")
    expected = ("http://example.com/path", "foo", "")
    assert got == expected


def test_get_credentials_uses_cached_credentials() -> None:
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://example.com/path")
    expected = ("http://example.com/path", "user", "pass")
    assert got == expected


def test_get_credentials_uses_cached_credentials_only_username() -> None:
    auth = MultiDomainBasicAuth()
    auth.passwords["example.com"] = ("user", "pass")

    got = auth._get_url_and_credentials("http://user@example.com/path")
    expected = ("http://example.com/path", "user", "pass")
    assert got == expected


def test_get_index_url_credentials() -> None:
    auth = MultiDomainBasicAuth(
        index_urls=[
            "http://example.com/",
            "http://foo:bar@example.com/path",
        ]
    )
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=False
    )

    # Check resolution of indexes
    assert get("http://example.com/path/path2") == ("foo", "bar")
    assert get("http://example.com/path3/path2") == (None, None)


def test_prioritize_longest_path_prefix_match_organization() -> None:
    auth = MultiDomainBasicAuth(
        index_urls=[
            "http://foo:bar@example.com/org-name-alpha/repo-alias/simple",
            "http://bar:foo@example.com/org-name-beta/repo-alias/simple",
        ]
    )
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=False
    )

    # Inspired by Azure DevOps URL structure, GitLab should look similar
    assert get("http://example.com/org-name-alpha/repo-guid/dowbload/") == (
        "foo",
        "bar",
    )
    assert get("http://example.com/org-name-beta/repo-guid/dowbload/") == ("bar", "foo")


def test_prioritize_longest_path_prefix_match_project() -> None:
    auth = MultiDomainBasicAuth(
        index_urls=[
            "http://foo:bar@example.com/org-alpha/project-name-alpha/repo-alias/simple",
            "http://bar:foo@example.com/org-alpha/project-name-beta/repo-alias/simple",
        ]
    )
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=False
    )

    # Inspired by Azure DevOps URL structure, GitLab should look similar
    assert get(
        "http://example.com/org-alpha/project-name-alpha/repo-guid/dowbload/"
    ) == ("foo", "bar")
    assert get(
        "http://example.com/org-alpha/project-name-beta/repo-guid/dowbload/"
    ) == ("bar", "foo")


class KeyringModuleV1:
    """Represents the supported API of keyring before get_credential
    was added.
    """

    def __init__(self) -> None:
        self.saved_passwords: list[tuple[str, str, str]] = []

    def get_password(self, system: str, username: str) -> str | None:
        if system == "example.com" and username:
            return username + "!netloc"
        if system == "http://example.com/path2/" and username:
            return username + "!url"
        return None

    def set_password(self, system: str, username: str, password: str) -> None:
        self.saved_passwords.append((system, username, password))


@pytest.mark.parametrize(
    "url, expect",
    [
        ("http://example.com/path1", (None, None)),
        # path1 URLs will be resolved by netloc
        ("http://user@example.com/path3", ("user", "user!netloc")),
        ("http://user2@example.com/path3", ("user2", "user2!netloc")),
        # path2 URLs will be resolved by index URL
        ("http://example.com/path2/path3", (None, None)),
        ("http://foo@example.com/path2/path3", ("foo", "foo!url")),
    ],
)
def test_keyring_get_password(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    expect: tuple[str | None, str | None],
) -> None:
    keyring = KeyringModuleV1()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/path2", "http://example.com/path3"],
        keyring_provider="import",
    )

    actual = auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True)
    assert actual == expect


def test_keyring_get_password_after_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    keyring = KeyringModuleV1()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(keyring_provider="import")

    def ask_input(prompt: str) -> str:
        assert prompt == "User for example.com: "
        return "user"

    monkeypatch.setattr("pip._internal.network.auth.ask_input", ask_input)
    actual = auth._prompt_for_password("example.com")
    assert actual == ("user", "user!netloc", False)


def test_keyring_get_password_after_prompt_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyring = KeyringModuleV1()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(keyring_provider="import")

    def ask_input(prompt: str) -> str:
        assert prompt == "User for unknown.com: "
        return "user"

    def ask_password(prompt: str) -> str:
        assert prompt == "Password: "
        return "fake_password"

    monkeypatch.setattr("pip._internal.network.auth.ask_input", ask_input)
    monkeypatch.setattr("pip._internal.network.auth.ask_password", ask_password)
    actual = auth._prompt_for_password("unknown.com")
    assert actual == ("user", "fake_password", True)


def test_keyring_get_password_username_in_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyring = KeyringModuleV1()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(
        index_urls=["http://user@example.com/path2", "http://example.com/path4"],
        keyring_provider="import",
    )
    get = functools.partial(
        auth._get_new_credentials, allow_netrc=False, allow_keyring=True
    )

    assert get("http://example.com/path2/path3") == ("user", "user!url")
    assert get("http://example.com/path4/path1") == (None, None)


@pytest.mark.parametrize(
    "response_status, creds, expect_save",
    [
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
    ],
)
def test_keyring_set_password(
    monkeypatch: pytest.MonkeyPatch,
    response_status: int,
    creds: tuple[str, str, bool],
    expect_save: bool,
) -> None:
    keyring = KeyringModuleV1()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(prompting=True, keyring_provider="import")
    monkeypatch.setattr(auth, "_get_url_and_credentials", lambda u: (u, None, None))
    monkeypatch.setattr(auth, "_prompt_for_password", lambda *a: creds)
    if creds[2]:
        # when _prompt_for_password indicates to save, we should save
        def should_save_password_to_keyring(*a: Any) -> bool:
            return True

    else:
        # when _prompt_for_password indicates not to save, we should
        # never call this function
        def should_save_password_to_keyring(*a: Any) -> bool:
            pytest.fail("_should_save_password_to_keyring should not be called")

    monkeypatch.setattr(
        auth, "_should_save_password_to_keyring", should_save_password_to_keyring
    )

    req = MockRequest("https://example.com")
    resp = MockResponse(b"")
    resp.url = req.url
    connection = MockConnection()

    def _send(sent_req: MockRequest, **kwargs: Any) -> MockResponse:
        assert sent_req is req
        assert "Authorization" in sent_req.headers
        r = MockResponse(b"")
        r.status_code = response_status
        return r

    # https://github.com/python/mypy/issues/2427
    connection._send = _send  # type: ignore[assignment]

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
        def __init__(self, username: str, password: str) -> None:
            self.username = username
            self.password = password

    def get_password(self, system: str, username: str) -> None:
        pytest.fail("get_password should not ever be called")

    def get_credential(self, system: str, username: str) -> Credential | None:
        if system == "http://example.com/path2/":
            return self.Credential("username", "url")
        if system == "example.com":
            return self.Credential("username", "netloc")
        return None


@pytest.mark.parametrize(
    "url, expect",
    [
        ("http://example.com/path1", ("username", "netloc")),
        ("http://example.com/path2/path3", ("username", "url")),
        ("http://user2@example.com/path2/path3", ("username", "url")),
    ],
)
def test_keyring_get_credential(
    monkeypatch: pytest.MonkeyPatch, url: str, expect: tuple[str, str]
) -> None:
    monkeypatch.setitem(sys.modules, "keyring", KeyringModuleV2())
    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/path1", "http://example.com/path2"],
        keyring_provider="import",
    )

    assert (
        auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True) == expect
    )


class KeyringModuleBroken:
    """Represents the current supported API of keyring, but broken"""

    def __init__(self) -> None:
        self._call_count = 0

    def get_credential(self, system: str, username: str) -> None:
        self._call_count += 1
        raise Exception("This keyring is broken!")


def test_broken_keyring_disables_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    keyring_broken = KeyringModuleBroken()
    monkeypatch.setitem(sys.modules, "keyring", keyring_broken)

    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/"], keyring_provider="import"
    )

    assert keyring_broken._call_count == 0
    for i in range(5):
        url = "http://example.com/path" + str(i)
        assert auth._get_new_credentials(
            url, allow_netrc=False, allow_keyring=True
        ) == (None, None)
        assert keyring_broken._call_count == 1


class KeyringSubprocessResult(KeyringModuleV1):
    """Represents the subprocess call to keyring"""

    returncode = 0  # Default to zero retcode

    def __call__(
        self,
        cmd: list[str],
        *,
        env: dict[str, str],
        stdin: Any | None = None,
        stdout: Any | None = None,
        input: bytes | None = None,
        check: bool | None = None,
    ) -> Any:
        if cmd[1] == "get":
            assert stdin == -3  # subprocess.DEVNULL
            assert stdout == subprocess.PIPE
            assert env["PYTHONIOENCODING"] == "utf-8"
            assert check is None

            password = self.get_password(*cmd[2:])
            if password is None:
                # Expect non-zero returncode if no password present
                self.returncode = 1
            else:
                # Passwords are returned encoded with a newline appended
                self.returncode = 0
                self.stdout = (password + os.linesep).encode("utf-8")

        if cmd[1] == "set":
            assert stdin is None
            assert stdout is None
            assert env["PYTHONIOENCODING"] == "utf-8"
            assert input is not None
            assert check

            # Input from stdin is encoded
            self.set_password(cmd[2], cmd[3], input.decode("utf-8").strip(os.linesep))

        return self

    def check_returncode(self) -> None:
        if self.returncode:
            raise Exception()


@pytest.mark.parametrize(
    "url, expect",
    [
        ("http://example.com/path1", (None, None)),
        # path1 URLs will be resolved by netloc
        ("http://user@example.com/path3", ("user", "user!netloc")),
        ("http://user2@example.com/path3", ("user2", "user2!netloc")),
        # path2 URLs will be resolved by index URL
        ("http://example.com/path2/path3", (None, None)),
        ("http://foo@example.com/path2/path3", ("foo", "foo!url")),
    ],
)
def test_keyring_cli_get_password(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    expect: tuple[str | None, str | None],
) -> None:
    monkeypatch.setattr(pip._internal.network.auth.shutil, "which", lambda x: "keyring")
    monkeypatch.setattr(
        pip._internal.network.auth.subprocess, "run", KeyringSubprocessResult()
    )
    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/path2", "http://example.com/path3"],
        keyring_provider="subprocess",
    )

    actual = auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True)
    assert actual == expect


@pytest.mark.parametrize(
    "response_status, creds, expect_save",
    [
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
    ],
)
def test_keyring_cli_set_password(
    monkeypatch: pytest.MonkeyPatch,
    response_status: int,
    creds: tuple[str, str, bool],
    expect_save: bool,
) -> None:
    monkeypatch.setattr(pip._internal.network.auth.shutil, "which", lambda x: "keyring")
    keyring = KeyringSubprocessResult()
    monkeypatch.setattr(pip._internal.network.auth.subprocess, "run", keyring)
    auth = MultiDomainBasicAuth(prompting=True, keyring_provider="subprocess")
    monkeypatch.setattr(auth, "_get_url_and_credentials", lambda u: (u, None, None))
    monkeypatch.setattr(auth, "_prompt_for_password", lambda *a: creds)
    if creds[2]:
        # when _prompt_for_password indicates to save, we should save
        def should_save_password_to_keyring(*a: Any) -> bool:
            return True

    else:
        # when _prompt_for_password indicates not to save, we should
        # never call this function
        def should_save_password_to_keyring(*a: Any) -> bool:
            pytest.fail("_should_save_password_to_keyring should not be called")

    monkeypatch.setattr(
        auth, "_should_save_password_to_keyring", should_save_password_to_keyring
    )

    req = MockRequest("https://example.com")
    resp = MockResponse(b"")
    resp.url = req.url
    connection = MockConnection()

    def _send(sent_req: MockRequest, **kwargs: Any) -> MockResponse:
        assert sent_req is req
        assert "Authorization" in sent_req.headers
        r = MockResponse(b"")
        r.status_code = response_status
        return r

    # https://github.com/python/mypy/issues/2427
    connection._send = _send  # type: ignore[assignment]

    resp.request = req
    resp.status_code = 401
    resp.connection = connection

    auth.handle_401(resp)

    if expect_save:
        assert keyring.saved_passwords == [("example.com", creds[0], creds[1])]
    else:
        assert keyring.saved_passwords == []
