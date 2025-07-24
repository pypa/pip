import os
import sys
import urllib.parse

from .compat import WINDOWS


def path_to_url(path: str, normalize_path: bool = True) -> str:
    """
    Convert a path to a file: URL with quoted path parts. The path will be
    normalized and made absolute if *normalize_path* is true (the default.)
    """
    if normalize_path:
        path = os.path.abspath(path)
    if WINDOWS:
        path = path.replace("\\", "/")

    drive, tail = os.path.splitdrive(path)
    if drive:
        if drive[:4] == "//?/":
            drive = drive[4:]
            if drive[:4].upper() == "UNC/":
                drive = "//" + drive[4:]
        if drive[1:] == ":":
            drive = "///" + drive
    elif tail.startswith("/"):
        tail = "//" + tail

    encoding = sys.getfilesystemencoding()
    errors = sys.getfilesystemencodeerrors()
    drive = urllib.parse.quote(drive, "/:", encoding, errors)
    tail = urllib.parse.quote(tail, "/", encoding, errors)
    return "file:" + drive + tail


def url_to_path(url: str) -> str:
    """
    Convert a file: URL to a path.
    """
    scheme, netloc, path = urllib.parse.urlsplit(url)[:3]
    assert scheme == "file" or scheme.endswith(
        "+file"
    ), f"You can only turn file: urls into filenames (not {url!r})"

    if WINDOWS:
        # e.g. file://c:/foo
        if netloc[1:2] == ":":
            path = netloc + path

        # e.g. file://server/share/foo
        elif netloc and netloc != "localhost":
            path = "//" + netloc + path

        # e.g. file://///server/share/foo
        elif path[:3] == "///":
            path = path[1:]

        # e.g. file:///c:/foo
        elif path[:1] == "/" and path[2:3] == ":":
            path = path[1:]

        path = path.replace("/", "\\")
    elif netloc and netloc != "localhost":
        raise ValueError(
            f"non-local file URIs are not supported on this platform: {url!r}"
        )

    encoding = sys.getfilesystemencoding()
    errors = sys.getfilesystemencodeerrors()
    return urllib.parse.unquote(path, encoding, errors)


def clean_file_url(url: str) -> str:
    """
    Fix up quoting and leading slashes in the given file: URL.

    e.g. 'file:/c:/foo bar@1.0' --> 'file:///c:/foo%20bar@1.0'.
    """
    # Replace "@" characters to protect them from percent-encoding.
    at_symbol_token = "---PIP_AT_SYMBOL---"
    assert at_symbol_token not in url
    url = url.replace("@", at_symbol_token)
    parts = urllib.parse.urlsplit(url)

    # Convert URL to a file path and back. This normalizes the netloc and
    # path, but resets the other URL components.
    tidy_url = path_to_url(url_to_path(url), normalize_path=False)
    tidy_parts = urllib.parse.urlsplit(tidy_url)

    # Restore the original scheme, query and fragment components.
    url = urllib.parse.urlunsplit(tidy_parts[:3] + parts[3:])
    url = url.replace(tidy_parts.scheme, parts.scheme, 1)

    # Restore "@" characters that were replaced earlier.
    return url.replace(at_symbol_token, "@")
