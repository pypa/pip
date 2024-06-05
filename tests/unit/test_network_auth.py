import contextlib
import functools
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

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
    input_url: str, url: str, username: Optional[str], password: Optional[str]
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
        self.saved_passwords: List[Tuple[str, str, str]] = []

    def get_password(self, system: str, username: str) -> Optional[str]:
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
    expect: Tuple[Optional[str], Optional[str]],
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
    creds: Tuple[str, str, bool],
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

    def __init__(self) -> None:
        self.saved_credential_by_username_by_system: dict[
            str, dict[str, KeyringModuleV2.Credential]
        ] = {}

    @dataclass
    class Credential:
        username: str
        password: str

    def get_password(self, system: str, username: str) -> None:
        pytest.fail("get_password should not ever be called")

    def get_credential(
        self, system: str, username: Optional[str]
    ) -> Optional[Credential]:
        credential_by_username = self.saved_credential_by_username_by_system.get(
            system, {}
        )
        if username is None:
            # Just return the first cred we can find (if
            # there even are any for this service).
            credentials = list(credential_by_username.values())
            if len(credentials) == 0:
                return None

            # Just pick the first one we can find.
            credential = credentials[0]
            return credential

        return credential_by_username.get(username)

    def set_password(self, system: str, username: str, password: str) -> None:
        if system not in self.saved_credential_by_username_by_system:
            self.saved_credential_by_username_by_system[system] = {}

        credential_by_username = self.saved_credential_by_username_by_system[system]
        assert username not in credential_by_username
        credential_by_username[username] = self.Credential(username, password)

    def delete_password(self, system: str, username: str) -> None:
        del self.saved_credential_by_username_by_system[system][username]

    @contextlib.contextmanager
    def add_credential(
        self, system: str, username: str, password: str
    ) -> Generator[None, None, None]:
        """
        Context manager that adds the given credential to the keyring
        and yields. Once the yield is done, the credential is removed
        from the keyring.

        This is re-entrant safe: it's ok for one thread to call this while in
        the middle of an existing invocation

        This is probably not thread safe: it's not ok for multiple threads to
        simultaneously call this method on the exact same instance of KeyringModuleV2.
        """
        self.set_password(system, username, password)
        try:
            yield
        finally:
            # No matter what happened, make sure we clean up after ourselves.
            self.delete_password(system, username)


@pytest.mark.parametrize(
    "url, expect",
    [
        ("http://example.com/path1", ("username", "hunter2")),
        ("http://example.com/path2/path3", ("username", "hunter3")),
        ("http://user2@example.com/path2/path3", ("user2", None)),
    ],
)
def test_keyring_get_credential(
    monkeypatch: pytest.MonkeyPatch, url: str, expect: Tuple[str, str]
) -> None:
    keyring = KeyringModuleV2()
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/path1", "http://example.com/path2"],
        keyring_provider="import",
    )

    with keyring.add_credential("example.com", "username", "hunter2"):
        with keyring.add_credential("http://example.com/path2/", "username", "hunter3"):
            assert (
                auth._get_new_credentials(url, allow_netrc=False, allow_keyring=True)
                == expect
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


class KeyringSubprocessResult(KeyringModuleV2):
    """Represents the subprocess call to keyring"""

    returncode = 0  # Default to zero retcode

    def __call__(
        self,
        cmd: List[str],
        *,
        env: Dict[str, str],
        stdin: Optional[Any] = None,
        stdout: Optional[Any] = None,
        input: Optional[bytes] = None,
        check: Optional[bool] = None,
    ) -> Any:
        parsed_cmd = list(cmd)
        assert parsed_cmd.pop(0) == "keyring"
        subcommand = [
            arg
            for arg in parsed_cmd
            # Skip past all the --whatever options until we get to the subcommand.
            if not arg.startswith("--")
        ][0]
        subcommand_func = {
            "get": self._get_subcommand,
            "set": self._set_subcommand,
        }[subcommand]

        subcommand_func(
            parsed_cmd,
            env=env,
            stdin=stdin,
            stdout=stdout,
            input=input,
            check=check,
        )

        return self

    def _get_subcommand(
        self,
        cmd: List[str],
        *,
        env: Dict[str, str],
        stdin: Optional[Any] = None,
        stdout: Optional[Any] = None,
        input: Optional[bytes] = None,
        check: Optional[bool] = None,
    ) -> None:
        assert cmd.pop(0) == "--mode=creds"
        assert cmd.pop(0) == "--output=json"
        assert stdin == -3  # subprocess.DEVNULL
        assert stdout == subprocess.PIPE
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert check is None
        assert cmd.pop(0) == "get"

        service = cmd.pop(0)
        username = cmd.pop(0) if len(cmd) > 0 else None
        creds = self.get_credential(service, username)
        if creds is None:
            # Expect non-zero returncode if no creds present
            self.returncode = 1
        else:
            # Passwords are returned encoded with a newline appended
            self.returncode = 0
            self.stdout = json.dumps(
                {
                    "username": creds.username,
                    "password": creds.password,
                }
            ).encode("utf-8")

    def _set_subcommand(
        self,
        cmd: List[str],
        *,
        env: Dict[str, str],
        stdin: Optional[Any] = None,
        stdout: Optional[Any] = None,
        input: Optional[bytes] = None,
        check: Optional[bool] = None,
    ) -> None:
        assert cmd.pop(0) == "set"
        assert stdin is None
        assert stdout is None
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert input is not None
        assert check

        # Input from stdin is encoded
        system, username = cmd
        self.set_password(system, username, input.decode("utf-8").strip(os.linesep))

    def check_returncode(self) -> None:
        if self.returncode:
            raise Exception()


@pytest.mark.parametrize(
    "url, expect",
    [
        # It's not obvious, but this url ultimately resolves to index url
        # http://example.com/path2, so we get the creds for that index.
        ("http://example.com/path1", ("saved-user1", "pw1")),
        ("http://saved-user1@example.com/path2", ("saved-user1", "pw1")),
        ("http://saved-user2@example.com/path2", ("saved-user2", "pw2")),
        ("http://new-user@example.com/path2", ("new-user", None)),
        ("http://example.com/path2/path3", ("saved-user1", "pw1")),
        ("http://foo@example.com/path2/path3", ("foo", None)),
    ],
)
def test_keyring_cli_get_password(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    expect: Tuple[Optional[str], Optional[str]],
) -> None:
    keyring_subprocess = KeyringSubprocessResult()
    monkeypatch.setattr(pip._internal.network.auth.shutil, "which", lambda x: "keyring")
    monkeypatch.setattr(
        pip._internal.network.auth.subprocess, "run", keyring_subprocess
    )
    auth = MultiDomainBasicAuth(
        index_urls=["http://example.com/path2", "http://example.com/path3"],
        keyring_provider="subprocess",
    )

    with keyring_subprocess.add_credential("example.com", "example", "!netloc"):
        with keyring_subprocess.add_credential(
            "http://example.com/path2/", "saved-user1", "pw1"
        ):
            with keyring_subprocess.add_credential(
                "http://example.com/path2/", "saved-user2", "pw2"
            ):
                actual = auth._get_new_credentials(
                    url, allow_netrc=False, allow_keyring=True
                )
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
    creds: Tuple[str, str, bool],
    expect_save: bool,
) -> None:
    expected_username, expected_password, save = creds
    monkeypatch.setattr(pip._internal.network.auth.shutil, "which", lambda x: "keyring")
    keyring = KeyringSubprocessResult()
    monkeypatch.setattr(pip._internal.network.auth.subprocess, "run", keyring)
    auth = MultiDomainBasicAuth(prompting=True, keyring_provider="subprocess")
    monkeypatch.setattr(auth, "_get_url_and_credentials", lambda u: (u, None, None))
    monkeypatch.setattr(auth, "_prompt_for_password", lambda *a: creds)
    if save:
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
        assert keyring.saved_credential_by_username_by_system == {
            "example.com": {
                expected_username: KeyringModuleV2.Credential(
                    expected_username, expected_password
                ),
            },
        }
    else:
        assert keyring.saved_credential_by_username_by_system == {}
