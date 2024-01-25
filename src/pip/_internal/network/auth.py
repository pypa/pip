"""Network Authentication Helpers

Contains interface (MultiDomainBasicAuth) and associated glue code for
providing credentials in the context of network requests.
"""
import logging
import os
import shutil
import subprocess
import sysconfig
import typing
import urllib.parse
from abc import ABC, abstractmethod
from functools import lru_cache
from os.path import commonprefix
from pathlib import Path
from typing import Any, List, NamedTuple, Optional, Tuple

from pip._vendor.requests.auth import AuthBase, HTTPBasicAuth
from pip._vendor.requests.models import Request, Response
from pip._vendor.requests.utils import get_netrc_auth

from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    ask,
    ask_input,
    ask_password,
    remove_auth_from_url,
    split_auth_netloc_from_url,
)
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
            stdout=subprocess.PIPE,
            env=env,
        )
        if res.returncode:
            return None
        return res.stdout.decode("utf-8").strip(os.linesep)

    def _set_password(self, service_name: str, username: str, password: str) -> None:
        """Mirror the implementation of keyring.set_password using cli"""
        if self.keyring is None:
            return None
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            [self.keyring, "set", service_name, username],
            input=f"{password}{os.linesep}".encode("utf-8"),
            env=env,
            check=True,
        )
        return None


@lru_cache(maxsize=None)
def get_keyring_provider(provider: str) -> KeyRingBaseProvider:
    logger.verbose("Keyring provider requested: %s", provider)

    # keyring has previously failed and been disabled
    if KEYRING_DISABLED:
        provider = "disabled"
    if provider in ["import", "auto"]:
        try:
            impl = KeyRingPythonProvider()
            logger.verbose("Keyring provider set: import")
            return impl
        except ImportError:
            pass
        except Exception as exc:
            # In the event of an unexpected exception
            # we should warn the user
            msg = "Installed copy of keyring fails with exception %s"
            if provider == "auto":
                msg = msg + ", trying to find a keyring executable as a fallback"
            logger.warning(msg, exc, exc_info=logger.isEnabledFor(logging.DEBUG))
    if provider in ["subprocess", "auto"]:
        cli = shutil.which("keyring")
        if cli and cli.startswith(sysconfig.get_path("scripts")):
            # all code within this function is stolen from shutil.which implementation
            @typing.no_type_check
            def PATH_as_shutil_which_determines_it() -> str:
                path = os.environ.get("PATH", None)
                if path is None:
                    try:
                        path = os.confstr("CS_PATH")
                    except (AttributeError, ValueError):
                        # os.confstr() or CS_PATH is not available
                        path = os.defpath
                # bpo-35755: Don't use os.defpath if the PATH environment variable is
                # set to an empty string

                return path

            scripts = Path(sysconfig.get_path("scripts"))

            paths = []
            for path in PATH_as_shutil_which_determines_it().split(os.pathsep):
                p = Path(path)
                try:
                    if not p.samefile(scripts):
                        paths.append(path)
                except FileNotFoundError:
                    pass

            path = os.pathsep.join(paths)

            cli = shutil.which("keyring", path=path)

        if cli:
            logger.verbose("Keyring provider set: subprocess with executable %s", cli)
            return KeyRingCliProvider(cli)

    logger.verbose("Keyring provider set: disabled")
    return KeyRingNullProvider()


class MultiDomainBasicAuth(AuthBase):
    def __init__(
        self,
        prompting: bool = True,
        index_urls: Optional[List[str]] = None,
        keyring_provider: str = "auto",
    ) -> None:
        self.prompting = prompting
        self.index_urls = index_urls
        self.keyring_provider = keyring_provider  # type: ignore[assignment]
        # In order to avoid prompting the user or its keyring repeatedly
        # we cache the credentials required per URL "prefix" and not just by
        # netloc. A single server might host multiple independent indexes with
        # independent credentials for them so we must be more specific than the
        # netloc, thus the URL "prefix".
        # The list is kept sorted by decreasing prefix length in order to guarantee
        # maximal specificity.
        self._required_credentials: list[Tuple[str, AuthInfo]] = []
        # When the user is prompted to enter credentials and keyring is
        # available, we will offer to save them. If the user accepts,
        # this value is set to the credentials they entered. After the
        # request authenticates, the caller should call
        # ``save_credentials`` to save these.
        self._credentials_to_save: Optional[Credentials] = None

    @property
    def keyring_provider(self) -> KeyRingBaseProvider:
        return get_keyring_provider(self._keyring_provider)

    @keyring_provider.setter
    def keyring_provider(self, provider: str) -> None:
        # The free function get_keyring_provider has been decorated with
        # functools.cache. If an exception occurs in get_keyring_auth that
        # cache will be cleared and keyring disabled, take that into account
        # if you want to remove this indirection.
        self._keyring_provider = provider

    @property
    def use_keyring(self) -> bool:
        # We won't use keyring when --no-input is passed unless
        # a specific provider is requested because it might require
        # user interaction
        return self.prompting or self._keyring_provider not in ["auto", "disabled"]

    def _get_keyring_auth(
        self,
        url: Optional[str],
        username: Optional[str],
    ) -> Optional[AuthInfo]:
        """Return the tuple auth for a given url from keyring."""
        # Do nothing if no url was provided
        if not url:
            return None

        try:
            return self.keyring_provider.get_auth_info(url, username)
        except Exception as exc:
            logger.warning(
                "Keyring is skipped due to an exception: %s",
                str(exc),
            )
            global KEYRING_DISABLED
            KEYRING_DISABLED = True
            get_keyring_provider.cache_clear()
            return None

    def _get_index_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Return the common prefix and original index URL matching the requested URL.

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

        url = remove_auth_from_url(url).rstrip("/") + "/"
        parsed_url = urllib.parse.urlsplit(url)

        candidates = []

        for index in self.index_urls:
            index = index.rstrip("/") + "/"
            index_without_auth = remove_auth_from_url(index)
            parsed_index = urllib.parse.urlsplit(index_without_auth)
            if parsed_url == parsed_index:
                return index_without_auth, index

            if parsed_url.netloc != parsed_index.netloc:
                continue

            candidate = urllib.parse.urlsplit(index)
            candidates.append(candidate)

        if not candidates:
            return None

        candidates.sort(
            reverse=True,
            key=lambda candidate: commonprefix(
                [
                    parsed_url.path,
                    candidate.path,
                ]
            ).rfind("/"),
        )

        index = urllib.parse.urlunsplit(candidates[0])
        common_path = (
            commonprefix([parsed_url.path, candidates[0].path]).rsplit("/", 1)[0] + "/"
        )
        matching_prefix = urllib.parse.urlunsplit(parsed_url._replace(path=common_path))
        return matching_prefix, index

    def _get_new_credentials(
        self,
        original_url: str,
    ) -> Tuple[str, AuthInfo]:
        """Find credentials for the specified URL and a key for caching them"""
        # Split the credentials and netloc from the url.
        url_without_auth, netloc, (username, password) = split_auth_netloc_from_url(
            original_url,
        )
        cache_key = url_without_auth

        # Start with the credentials embedded in the url
        if username is not None and password is not None:
            logger.debug("Found credentials in url for %s", cache_key)
            return cache_key, (username, password)

        # Find a matching index url for this request
        index_info = self._get_index_url(url_without_auth)
        if index_info:
            cache_key, index_url = index_info
            # Split the credentials from the url.
            (
                url_without_auth,
                _,
                (index_username, password),
            ) = split_auth_netloc_from_url(index_url)
            logger.debug("Found index url %s", url_without_auth)

            # If an index URL was found, try its embedded credentials as long as the
            # original and index urls agree on the username.
            if (
                index_username is not None
                and password is not None
                and username in (index_username, None)
            ):
                logger.debug("Found credentials in index url for %s", cache_key)
                return cache_key, (index_username, password)

            # Use the username from the index only if the original does not specify one
            if username is None:
                username = index_username

        if self.use_keyring:
            # We still don't have a password so let's lookup up the url_without_auth in
            # the keyring. Note that this is the original_url (without auth) if we did
            # not find a matching index otherwise it's the index url (without auth).
            kr_auth = self._get_keyring_auth(url_without_auth, username)
            if kr_auth is None:
                # Still no password so let's try with the netloc only. That also means
                # we'll have to cache credentials for a minimal url, i.e.:
                # scheme://netloc/.
                scheme, netloc, *_ = urllib.parse.urlsplit(cache_key)
                cache_key = urllib.parse.urlunsplit((scheme, netloc, "/", None, None))
                kr_auth = self._get_keyring_auth(netloc, username)
            if kr_auth and (  # we found some credentials and
                username is None  # the URL does not constrain the username
                or kr_auth[0] == username  # or credentials are for the same user
            ):
                logger.debug("Found credentials in keyring for %s", cache_key)
                return cache_key, kr_auth

        # As a last resort, try with netrc. This is as specific as the netloc so we
        # have to cache credentials for a minimal url, i.e.: scheme://netloc/.
        scheme, netloc, *_ = urllib.parse.urlsplit(cache_key)
        cache_key = urllib.parse.urlunsplit((scheme, netloc, "/", None, None))
        netrc_auth = get_netrc_auth(original_url)
        if netrc_auth:
            logger.debug("Found credentials in netrc for %s", cache_key)
            return cache_key, netrc_auth

        # Either username and password are None because neither the original_url nor any
        # matching index had credentials and we did not find any entry in keyring or
        # netrc.
        # Or username is not None and password is None in case the original_url or any
        # matching index_url has a userinfo without a `:<password>` and we did not find
        # any entry in keyring or netrc to complement the username with a password.
        # If both a username and password where found (even if being empty strings) we
        # would have exited earlier.
        if username is None and password is None:
            logger.debug("No credentials found for %s", cache_key)
        else:
            logger.debug(
                "No password found for %s. Will assume username is a token.", cache_key
            )
        return cache_key, (username, password)

    def _get_required_credentials(self, url_without_auth: str) -> AuthInfo:
        """Return the credentials that were found to be required for the given URL.

        The URL must not contain any auth.
        """
        # Check if a similar URL is known to require credentials
        for url_prefix, credentials in self._required_credentials:
            if url_without_auth.startswith(url_prefix):
                logger.debug("Found required credentials for %s", url_prefix)
                return credentials

        # We're not aware of any required credentials for a similar URL.
        # We might find out it is the case only after the server answered with
        # a 401 Unauthorized response.
        return None, None

    def _cache_required_credentials(
        self, url_prefix: str, credentials: AuthInfo
    ) -> None:
        self._required_credentials = sorted(
            self._required_credentials + [(url_prefix, credentials)],
            reverse=True,
            key=lambda v: len(v[0]),
        )

    def __call__(self, req: Request) -> Request:
        # Set the url of the request to the url without any credentials
        req.url = remove_auth_from_url(req.url)

        # Get credentials for this request if they're required
        username, password = self._get_required_credentials(req.url)

        if username is not None and password is not None:
            # Send the basic auth with this request
            req = HTTPBasicAuth(username, password)(req)

        # Attach a hook to handle 401 responses
        req.register_hook("response", self.handle_401)

        return req

    # Factored out to allow for easy patching in tests
    def _prompt_for_password(
        self, netloc: str
    ) -> Tuple[Optional[str], Optional[str], bool]:
        username = ask_input(f"User for {netloc}: ") if self.prompting else None
        if not username:
            return None, None, False
        if self.use_keyring:
            auth = self._get_keyring_auth(netloc, username)
            if auth and auth[0] is not None and auth[1] is not None:
                return auth[0], auth[1], False
        password = ask_password("Password: ")
        return username, password, True

    # Factored out to allow for easy patching in tests
    def _should_save_password_to_keyring(self) -> bool:
        if (
            not self.prompting
            or not self.use_keyring
            or not self.keyring_provider.has_keyring
        ):
            return False
        return ask("Save credentials to keyring [y/N]: ", ["y", "n"]) == "y"

    def handle_401(self, resp: Response, **kwargs: Any) -> Response:
        # We only care about 401 responses, anything else we want to just
        #   pass through the actual response
        if resp.status_code != 401:
            return resp

        cache_key, (username, password) = self._get_new_credentials(resp.url)

        # We are not able to prompt the user so simply return the response
        if not self.prompting and not username and not password:
            return resp

        parsed = urllib.parse.urlparse(resp.url)

        # Prompt the user for a new username and password
        save = False
        if not username and not password:
            username, password, save = self._prompt_for_password(parsed.netloc)
            if username:
                # As we prompted the user for credentials for the netloc and
                # not a more specific URL, we will cache them for the least
                # specific URL, i.e.: scheme://netloc/
                scheme, netloc, *_ = parsed
                cache_key = urllib.parse.urlunsplit((scheme, netloc, "/", None, None))

        # Store the new username and password to use for future requests
        self._credentials_to_save = None
        if username is not None:
            self._cache_required_credentials(cache_key, (username, password))
            # Prompt to save the password to keyring
            if (
                save
                and password is not None
                and self._should_save_password_to_keyring()
            ):
                self._credentials_to_save = Credentials(
                    url=parsed.netloc,
                    username=username,
                    password=password,
                )

        # Consume content and release the original connection to allow our new
        #   request to reuse the same one.
        # The result of the assignment isn't used, it's just needed to consume
        # the content.
        _ = resp.content
        resp.raw.release_conn()

        # Add our new username and password to the request
        req = HTTPBasicAuth(username or "", password or "")(resp.request)
        req.register_hook("response", self.warn_on_401)

        # On successful request, save the credentials that were used to
        # keyring. (Note that if the user responded "no" above, this member
        # is not set and nothing will be saved.)
        if self._credentials_to_save:
            req.register_hook("response", self.save_credentials)

        # Send our new request
        new_resp = resp.connection.send(req, **kwargs)
        new_resp.history.append(resp)

        return new_resp

    def warn_on_401(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to warn about incorrect credentials."""
        if resp.status_code == 401:
            logger.warning(
                "401 Error, Credentials not correct for %s",
                resp.request.url,
            )

    def save_credentials(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to save credentials on success."""
        assert (
            self.keyring_provider.has_keyring
        ), "should never reach here without keyring"

        creds = self._credentials_to_save
        self._credentials_to_save = None
        if creds and resp.status_code < 400:
            try:
                logger.info("Saving credentials to keyring")
                self.keyring_provider.save_auth_info(
                    creds.url, creds.username, creds.password
                )
            except Exception:
                logger.exception("Failed to save credentials")
