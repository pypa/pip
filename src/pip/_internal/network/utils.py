import logging
import urllib.parse
from http.client import RemoteDisconnected
from typing import Dict, Generator, Literal, Optional

from pip._vendor import requests, urllib3
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, Response

from pip._internal.exceptions import (
    ConnectionFailedError,
    ConnectionTimeoutError,
    NetworkConnectionError,
    ProxyConnectionError,
    SSLVerificationError,
)
from pip._internal.utils.compat import has_tls
from pip._internal.utils.logging import VERBOSE

# The following comments and HTTP headers were originally added by
# Donald Stufft in git commit 22c562429a61bb77172039e480873fb239dd8c03.
#
# We use Accept-Encoding: identity here because requests defaults to
# accepting compressed responses. This breaks in a variety of ways
# depending on how the server is configured.
# - Some servers will notice that the file isn't a compressible file
#   and will leave the file alone and with an empty Content-Encoding
# - Some servers will notice that the file is already compressed and
#   will leave the file alone, adding a Content-Encoding: gzip header
# - Some servers won't notice anything at all and will take a file
#   that's already been compressed and compress it again, and set
#   the Content-Encoding: gzip header
# By setting this to request only the identity encoding we're hoping
# to eliminate the third case.  Hopefully there does not exist a server
# which when given a file will notice it is already compressed and that
# you're not asking for a compressed file and will then decompress it
# before sending because if that's the case I don't think it'll ever be
# possible to make this work.
HEADERS: Dict[str, str] = {"Accept-Encoding": "identity"}


def raise_for_status(resp: Response) -> None:
    http_error_msg = ""
    if isinstance(resp.reason, bytes):
        # We attempt to decode utf-8 first because some servers
        # choose to localize their reason strings. If the string
        # isn't utf-8, we fall back to iso-8859-1 for all other
        # encodings.
        try:
            reason = resp.reason.decode("utf-8")
        except UnicodeDecodeError:
            reason = resp.reason.decode("iso-8859-1")
    else:
        reason = resp.reason

    if 400 <= resp.status_code < 500:
        http_error_msg = (
            f"{resp.status_code} Client Error: {reason} for url: {resp.url}"
        )

    elif 500 <= resp.status_code < 600:
        http_error_msg = (
            f"{resp.status_code} Server Error: {reason} for url: {resp.url}"
        )

    if http_error_msg:
        raise NetworkConnectionError(http_error_msg, response=resp)


def response_chunks(
    response: Response, chunk_size: int = CONTENT_CHUNK_SIZE
) -> Generator[bytes, None, None]:
    """Given a requests Response, provide the data chunks."""
    try:
        # Special case for urllib3.
        for chunk in response.raw.stream(
            chunk_size,
            # We use decode_content=False here because we don't
            # want urllib3 to mess with the raw bytes we get
            # from the server. If we decompress inside of
            # urllib3 then we cannot verify the checksum
            # because the checksum will be of the compressed
            # file. This breakage will only occur if the
            # server adds a Content-Encoding header, which
            # depends on how the server was configured:
            # - Some servers will notice that the file isn't a
            #   compressible file and will leave the file alone
            #   and with an empty Content-Encoding
            # - Some servers will notice that the file is
            #   already compressed and will leave the file
            #   alone and will add a Content-Encoding: gzip
            #   header
            # - Some servers won't notice anything at all and
            #   will take a file that's already been compressed
            #   and compress it again and set the
            #   Content-Encoding: gzip header
            #
            # By setting this not to decode automatically we
            # hope to eliminate problems with the second case.
            decode_content=False,
        ):
            yield chunk
    except AttributeError:
        # Standard file-like object.
        while True:
            chunk = response.raw.read(chunk_size)
            if not chunk:
                break
            yield chunk


def raise_connection_error(error: requests.ConnectionError, *, timeout: float) -> None:
    """Raise a specific error for a given ConnectionError, if possible.

    Note: requests.ConnectionError is the parent class of
          requests.ProxyError, requests.SSLError, and requests.ConnectTimeout
          so these errors are also handled here. In addition, a ReadTimeout
          wrapped in a requests.MayRetryError is converted into a
          ConnectionError by requests internally.
    """
    # NOTE: this function was written defensively to degrade gracefully when
    # a specific error cannot be raised due to issues inspecting the exception
    # state. This logic isn't pretty.

    url = error.request.url
    # requests.ConnectionError.args[0] should be an instance of
    # urllib3.exceptions.MaxRetryError.
    reason = error.args[0]
    # Attempt to query the host from the urllib3 error, otherwise fall back to
    # parsing the request URL.
    if isinstance(reason, urllib3.exceptions.MaxRetryError):
        host = reason.pool.host
        # Narrow the reason further to the specific error from the last retry.
        reason = reason.reason
    else:
        host = urllib.parse.urlsplit(error.request.url).netloc

    if isinstance(reason, urllib3.exceptions.SSLError):
        raise SSLVerificationError(url, host, reason, is_tls_available=has_tls())
    # NewConnectionError is a subclass of TimeoutError for some reason ...
    if isinstance(reason, urllib3.exceptions.TimeoutError) and not isinstance(
        reason, urllib3.exceptions.NewConnectionError
    ):
        kind: Literal["connect", "read"] = (
            "connect"
            if isinstance(reason, urllib3.exceptions.ConnectTimeoutError)
            else "read"
        )
        raise ConnectionTimeoutError(url, host, kind=kind, timeout=timeout)
    if isinstance(reason, urllib3.exceptions.ProxyError):
        raise ProxyConnectionError(url, host, reason)

    # Unknown error, give up and raise a generic error.
    raise ConnectionFailedError(url, host, reason)


class Urllib3RetryFilter:
    """A logging filter which attempts to rewrite urllib3's retrying
    warnings to be more readable and less technical.
    """

    def __init__(self, *, timeout: Optional[float]) -> None:
        self.timeout = timeout
        self.verbose = logging.getLogger().isEnabledFor(VERBOSE)  # HACK

    def filter(self, record: logging.LogRecord) -> bool:
        # Attempt to "sniff out" the retrying warning.
        if not isinstance(record.args, tuple):
            return True

        retry = next(
            (a for a in record.args if isinstance(a, urllib3.util.Retry)), None
        )
        if record.levelno != logging.WARNING or retry is None:
            # Not the right warning, leave it alone.
            return True

        error = next((a for a in record.args if isinstance(a, Exception)), None)
        if error is None:
            # No error information available, leave it alone.
            return True

        rewritten = False
        if isinstance(error, urllib3.exceptions.NewConnectionError):
            rewritten = True
            connection = error.pool
            record.msg = f"failed to connect to {connection.host}"
            if isinstance(connection, urllib3.connection.HTTPSConnection):
                record.msg += " via HTTPS"
            elif isinstance(connection, urllib3.connection.HTTPConnection):
                record.msg += " via HTTP"
        elif isinstance(error, urllib3.exceptions.SSLError):
            rewritten = True
            # Yes, this is the most information we can provide as urllib3
            # doesn't give us much.
            record.msg = "SSL verification failed"
        elif isinstance(error, urllib3.exceptions.TimeoutError):
            rewritten = True
            record.msg = f"server didn't respond within {self.timeout} seconds"
        elif isinstance(error, urllib3.exceptions.ProtocolError):
            try:
                if isinstance(error.args[1], RemoteDisconnected):
                    rewritten = True
                    record.msg = "Server closed connection unexpectedly"
            except IndexError:
                pass
        elif isinstance(error, urllib3.exceptions.ProxyError):
            rewritten = True
            record.msg = "failed to connect to proxy"
            try:
                reason = error.args[1]
                proxy = reason.pool.host
            except Exception:
                pass
            else:
                record.msg += f" {proxy}"

        if rewritten:
            # The total remaining retries is already decremented when this
            # warning is raised.
            retries = retry.total + 1
            assert isinstance(retry, urllib3.util.Retry)
            if retries > 1:
                record.msg += f", retrying {retries} more times"
            elif retries == 1:
                record.msg += ", retrying 1 last time"

            if self.verbose:
                # As it's hard to provide enough detail, show the original
                # error under verbose mode.
                record.msg += f": {error!s}"
            record.args = ()

        return True
