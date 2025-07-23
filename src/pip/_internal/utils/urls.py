import itertools
import os
import re
import string
import urllib.parse
import urllib.request

from pip._internal.utils.misc import pairwise

from .compat import WINDOWS


def path_to_url(path: str) -> str:
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
    url = urllib.parse.urljoin("file:", urllib.request.pathname2url(path))
    return url


def url_to_path(url: str) -> str:
    """
    Convert a file: URL to a path.
    """
    assert url.startswith(
        "file:"
    ), f"You can only turn file: urls into filenames (not {url!r})"

    _, netloc, path, _, _ = urllib.parse.urlsplit(url)

    if not netloc or netloc == "localhost":
        # According to RFC 8089, same as empty authority.
        netloc = ""
    elif WINDOWS:
        # If we have a UNC path, prepend UNC share notation.
        netloc = "\\\\" + netloc
    else:
        raise ValueError(
            f"non-local file URIs are not supported on this platform: {url!r}"
        )

    path = urllib.request.url2pathname(netloc + path)

    # On Windows, urlsplit parses the path as something like "/C:/Users/foo".
    # This creates issues for path-related functions like io.open(), so we try
    # to detect and strip the leading slash.
    if (
        WINDOWS
        and not netloc  # Not UNC.
        and len(path) >= 3
        and path[0] == "/"  # Leading slash to strip.
        and path[1] in string.ascii_letters  # Drive letter.
        and path[2:4] in (":", ":/")  # Colon + end of string, or colon + absolute path.
    ):
        path = path[1:]

    return path


def _clean_url_path_part(part: str) -> str:
    """
    Clean a "part" of a URL path (i.e. after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    return urllib.parse.quote(urllib.parse.unquote(part))


def _clean_file_url_path(part: str) -> str:
    """
    Clean the first part of a URL path that corresponds to a local
    filesystem path (i.e. the first part after splitting on "@" characters).
    """
    # We unquote prior to quoting to make sure nothing is double quoted.
    # Also, on Windows the path part might contain a drive letter which
    # should not be quoted. On Linux where drive letters do not
    # exist, the colon should be quoted. We rely on urllib.request
    # to do the right thing here.
    return urllib.request.pathname2url(urllib.request.url2pathname(part))


# percent-encoded:                   /
_reserved_chars_re = re.compile("(@|%2F)", re.IGNORECASE)


def _clean_url_path(path: str, is_local_path: bool) -> str:
    """
    Clean the path portion of a URL.
    """
    if is_local_path:
        clean_func = _clean_file_url_path
    else:
        clean_func = _clean_url_path_part

    # Split on the reserved characters prior to cleaning so that
    # revision strings in VCS URLs are properly preserved.
    parts = _reserved_chars_re.split(path)

    cleaned_parts = []
    for to_clean, reserved in pairwise(itertools.chain(parts, [""])):
        cleaned_parts.append(clean_func(to_clean))
        # Normalize %xx escapes (e.g. %2f -> %2F)
        cleaned_parts.append(reserved.upper())

    return "".join(cleaned_parts)


def clean_url(url: str) -> str:
    """
    Make sure a link is fully quoted.
    For example, if ' ' occurs in the URL, it will be replaced with "%20",
    and without double-quoting other characters.
    """
    # Split the URL into parts according to the general structure
    # `scheme://netloc/path?query#fragment`.
    result = urllib.parse.urlsplit(url)
    # If the netloc is empty, then the URL refers to a local filesystem path.
    is_local_path = not result.netloc
    path = _clean_url_path(result.path, is_local_path=is_local_path)
    return urllib.parse.urlunsplit(result._replace(path=path))
