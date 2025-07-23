import os
import sys
import urllib.parse

from .compat import WINDOWS


def path_to_url(path: str, normalize_path: bool = True) -> str:
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    if normalize_path:
        path = os.path.abspath(path)
    if WINDOWS:
        path = path.replace("\\", "/")
    encoding = sys.getfilesystemencoding()
    errors = sys.getfilesystemencodeerrors()

    drive, tail = os.path.splitdrive(path)
    if drive:
        if drive[:4] == "//?/":
            drive = drive[4:]
            if drive[:4].upper() == "UNC/":
                drive = "//" + drive[4:]
        if drive[1:] == ":":
            drive = "///" + drive
        drive = urllib.parse.quote(drive, "/:", encoding, errors)
    elif tail.startswith("/"):
        tail = "//" + tail
    tail = urllib.parse.quote(tail, "/", encoding, errors)
    return "file:" + drive + tail


def url_to_path(url: str) -> str:
    """
    Convert a file: URL to a path.
    """
    scheme, netloc, path, _, _ = urllib.parse.urlsplit(url)
    assert scheme == "file" or scheme.endswith(
        "+file"
    ), f"You can only turn file: urls into filenames (not {url!r})"

    if WINDOWS:
        if netloc:
            if netloc[1:] == ":":
                path = netloc + path
            elif netloc != "localhost":
                path = "//" + netloc + path
        elif path[:3] == "///":
            path = path[1:]
        else:
            if path[:1] == "/" and path[2:3] in (":", "|"):
                path = path[1:]
            if path[1:2] == "|":
                path = path[:1] + ":" + path[2:]
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

    e.g. 'file:/c:/foo bar' --> 'file:///c:/foo%20bar'.
    """
    tok = "-_-PIP_AT_SYMBOL_-_"
    assert tok not in url
    orig_url = url.replace("@", tok)
    tidy_url = path_to_url(url_to_path(orig_url), normalize_path=False)
    tidy_parts = urllib.parse.urlsplit(tidy_url)
    orig_parts = urllib.parse.urlsplit(orig_url)
    merged_url = urllib.parse.urlunsplit(tidy_parts[:3] + orig_parts[3:])
    if orig_parts.scheme != "file":
        merged_url = orig_parts.scheme + merged_url[4:]
    return merged_url.replace(tok, "@")
