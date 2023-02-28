"""Network Authentication Helpers

Contains interface (MultiDomainBasicAuth) and associated glue code for
providing credentials in the context of network requests.
"""

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, NamedTuple, Optional, Tuple

from pip._vendor.requests.auth import AuthBase, HTTPBasicAuth
from pip._vendor.requests.models import Request
from pip._vendor.requests.utils import get_netrc_auth

from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import remove_auth_from_url, split_auth_netloc_from_url
from pip._internal.vcs.versioncontrol import AuthInfo

logger = getLogger(__name__)

KEYRING_DISABLED = False


class Credentials(NamedTuple):
    url: str
    username: str
    password: str


class KeyRingBaseProvider(ABC):
    """Keyring base provider interface"""

    has_keyring: bool

    @abstractmethod
    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        ...

    @abstractmethod
    def save_auth_info(self, url: str, username: str, password: str) -> None:
        ...


class KeyRingNullProvider(KeyRingBaseProvider):
    """Keyring null provider"""

    has_keyring = False

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return None


class KeyRingPythonProvider(KeyRingBaseProvider):
    """Keyring interface which uses locally imported `keyring`"""

    has_keyring = True

    def __init__(self) -> None:
        import keyring

        self.keyring = keyring

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # Support keyring's get_credential interface which supports getting
        # credentials without a username. This is only available for
        # keyring>=15.2.0.
        if hasattr(self.keyring, "get_credential"):
            logger.debug("Getting credentials from keyring for %s", url)
            cred = self.keyring.get_credential(url, username)
            if cred is not None:
                return cred.username, cred.password
            return None

        if username is not None:
            logger.debug("Getting password from keyring for %s", url)
            password = self.keyring.get_password(url, username)
            if password:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        self.keyring.set_password(url, username, password)


class KeyRingCliProvider(KeyRingBaseProvider):
    """Provider which uses `keyring` cli

    Instead of calling the keyring package installed alongside pip
    we call keyring on the command line which will enable pip to
    use which ever installation of keyring is available first in
    PATH.
    """

    has_keyring = True

    def __init__(self, cmd: str) -> None:
        self.keyring = cmd

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # This is the default implementation of keyring.get_credential
        # https://github.com/jaraco/keyring/blob/97689324abcf01bd1793d49063e7ca01e03d7d07/keyring/backend.py#L134-L139
        if username is not None:
            password = self._get_password(url, username)
            if password is not None:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return self._set_password(url, username, password)

    def _get_password(self, service_name: str, username: str) -> Optional[str]:
        """Mirror the implementation of keyring.get_password using cli"""
        if self.keyring is None:
            return None

        cmd = [self.keyring, "get", service_name, username]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=env,
        )
        if res.returncode:
            return None
        return res.stdout.decode("utf-8").strip(os.linesep)

    def _set_password(self, service_name: str, username: str, password: str) -> None:
        """Mirror the implementation of keyring.set_password using cli"""
        if self.keyring is None:
            return None

        cmd = [self.keyring, "set", service_name, username]
        input_ = (password + os.linesep).encode("utf-8")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(cmd, input=input_, env=env)
        res.check_returncode()
        return None


def get_keyring_provider() -> KeyRingBaseProvider:
    # keyring has previously failed and been disabled
    if not KEYRING_DISABLED:
        # Default to trying to use Python provider
        try:
            return KeyRingPythonProvider()
        except ImportError:
            pass
        except Exception as exc:
            # In the event of an unexpected exception
            # we should warn the user
            logger.warning(
                "Installed copy of keyring fails with exception %s, "
                "trying to find a keyring executable as a fallback",
                str(exc),
            )

        # Fallback to Cli Provider if `keyring` isn't installed
        cli = shutil.which("keyring")
        if cli:
            return KeyRingCliProvider(cli)

    return KeyRingNullProvider()


def get_keyring_auth(url: Optional[str], username: Optional[str]) -> Optional[AuthInfo]:
    """Return the tuple auth for a given url from keyring."""
    # Do nothing if no url was provided
    if not url:
        return None

    keyring = get_keyring_provider()
    try:
        return keyring.get_auth_info(url, username)
    except Exception as exc:
        logger.warning(
            "Keyring is skipped due to an exception: %s",
            str(exc),
        )
        global KEYRING_DISABLED
        KEYRING_DISABLED = True
        return None


class MultiDomainBasicAuth(AuthBase):
    def __init__(
        self,
        prompting: bool = True,
        index_urls: Optional[List[str]] = None,
        default_key_ring_user: Optional[str] = None,
    ) -> None:
        self.prompting = prompting
        self.index_urls = index_urls
        self.passwords: Dict[str, AuthInfo] = {}
        self.default_key_ring_user = default_key_ring_user
        # When the user is prompted to enter credentials and keyring is
        # available, we will offer to save them. If the user accepts,
        # this value is set to the credentials they entered. After the
        # request authenticates, the caller should call
        # ``save_credentials`` to save these.
        self._credentials_to_save: Optional[Credentials] = None

    def _get_index_url(self, url: str) -> Optional[str]:
        """Return the original index URL matching the requested URL.

        Cached or dynamically generated credentials may work against
        the original index URL rather than just the netloc.

        The provided url should have had its username and password
        removed already. If the original index url had credentials then
        they will be included in the return value.

        Returns None if no matching index was found, or if --no-index
        was specified by the user.
        """
        if not url or not self.index_urls:
            return None

        for u in self.index_urls:
            prefix = remove_auth_from_url(u).rstrip("/") + "/"
            if url.startswith(prefix):
                return u
        return None

    def _get_new_credentials(
        self,
        original_url: str,
    ) -> AuthInfo:
        """Find and return credentials for the specified URL."""
        # Split the credentials and netloc from the url.
        url, netloc, url_user_password = split_auth_netloc_from_url(
            original_url,
        )

        username, password = url_user_password
        if username is not None and password is not None:
            logger.debug("Found credentials in url for %s", netloc)
            return url_user_password

        def split_index_url_on_url_and_credentials(url):
            if not url:
                return url, None
            index_info = split_auth_netloc_from_url(url)
            if not index_info:
                return url, None
            index_url, _, index_url_user_password = index_info
            logger.debug("Found index url %s", index_url)
            return index_url, index_url_user_password

        index_url, index_url_user_password = split_index_url_on_url_and_credentials(
            self._get_index_url(url)
        )

        # If an index URL was found, try its embedded credentials
        if index_url and index_url_user_password[0] is not None:
            username, password = index_url_user_password
            if username is not None and password is not None:
                logger.debug("Found credentials in index url for %s", netloc)
                return index_url_user_password

        netrc_auth = get_netrc_auth(original_url)
        if netrc_auth is not None:
            logger.debug("Found credentials in netrc for %s", netloc)
            return netrc_auth

        kr_auth = self._find_key_ring_credentials(
            index_url, index_url_user_password, netloc, username
        )
        if kr_auth is not None:
            return kr_auth

        return username, password

    def _find_key_ring_credentials(
        self,
        index_url: Optional[str],
        index_url_user_password: Optional[str],
        netloc: str,
        artifact_username: str,
    ) -> Optional[AuthInfo]:
        def get_key_ring_user() -> Optional[str]:
            if artifact_username is not None:
                return artifact_username
            if index_url_user_password:
                if (
                    index_url_user_password[0] is not None
                    and index_url_user_password[1] is None
                ):
                    logger.debug("Found key ring username in index_url")
                    return index_url_user_password[0]
            if artifact_username is None and self.default_key_ring_user is not None:
                logger.debug("Using default_key_ring_user")
                return self.default_key_ring_user
            return None

        key_ring_user = get_key_ring_user()
        if key_ring_user is None:
            return None

        if index_url is not None:
            kr_auth = get_keyring_auth(index_url, key_ring_user)
            if kr_auth:
                logger.debug("Found credentials in keyring for %s", index_url)
                return kr_auth

        kr_auth = get_keyring_auth(netloc, key_ring_user)
        if kr_auth:
            logger.debug("Found credentials in keyring for %s", netloc)
            return kr_auth

        return None

    def _get_url_and_credentials(
        self, original_url: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Return the credentials to use for the provided URL.

        If allowed, netrc and keyring may be used to obtain the
        correct credentials.

        Returns (url_without_credentials, username, password). Note
        that even if the original URL contains credentials, this
        function may return a different username and password.
        """
        url, netloc, _ = split_auth_netloc_from_url(original_url)

        # Try to get credentials from original url
        username, password = self._get_new_credentials(original_url)

        # If credentials not found, use any stored credentials for this netloc.
        # Do this if either the username or the password is missing.
        # This accounts for the situation in which the user has specified
        # the username in the index url, but the password comes from keyring.
        if (username is None or password is None) and netloc in self.passwords:
            un, pw = self.passwords[netloc]
            # It is possible that the cached credentials are for a different username,
            # in which case the cache should be ignored.
            if username is None or username == un:
                username, password = un, pw

        if username is not None or password is not None:
            # Convert the username and password if they're None, so that
            # this netloc will show up as "cached" in the conditional above.
            # Further, HTTPBasicAuth doesn't accept None, so it makes sense to
            # cache the value that is going to be used.
            username = username or ""
            password = password or ""

            # Store any acquired credentials.
            self.passwords[netloc] = (username, password)

        assert (
            # Credentials were found
            (username is not None and password is not None)
            # Credentials were not found
            or (username is None and password is None)
        ), f"Could not load credentials from url: {original_url}"

        return url, username, password

    def __call__(self, req: Request) -> Request:
        # Get credentials for this request
        url, username, password = self._get_url_and_credentials(req.url)

        # Set the url of the request to the url without any credentials
        req.url = url

        if username is not None and password is not None:
            # Send the basic auth with this request
            req = HTTPBasicAuth(username, password)(req)
        return req
