import os
import sys
import urllib.parse

from .compat import WINDOWS


def path_to_url(path: str) -> str:
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
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
    assert url.startswith(
        "file:"
    ), f"You can only turn file: urls into filenames (not {url!r})"

    _, netloc, path, _, _ = urllib.parse.urlsplit(url)

    if WINDOWS:
        if netloc and netloc != "localhost":
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
