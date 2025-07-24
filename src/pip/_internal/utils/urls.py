import os
import string
import urllib.parse
import urllib.request

from .compat import WINDOWS


def path_to_url(path: str, normalize_path=True) -> str:
    """
    Convert a path to a file: URL with quoted path parts.  The path will be
    normalized and made absolute if *normalize_path* is true (the default.)
    """
    if normalize_path:
        path = os.path.abspath(path)
    url = urllib.parse.urljoin("file://", urllib.request.pathname2url(path))
    return url


def url_to_path(url: str) -> str:
    """
    Convert a file: URL to a path.
    """
    scheme, netloc, path = urllib.parse.urlsplit(url)[:3]
    assert scheme == "file" or scheme.endswith(
        "+file"
    ), f"You can only turn file: urls into filenames (not {url!r})"

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
