import mimetypes
import os
import shutil
import sys

from pip._internal.download import logger
from pip._internal.exceptions import HashMismatch

from pip._internal.utils.misc import rmtree, ask_path_exists, display_path, backup_dir
from pip._internal.utils.unpacking import logger, unpack_file


def url_to_path(url):
    # type: (str) -> str
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)

    _, netloc, path, _, _ = urllib_parse.urlsplit(url)

    if not netloc or netloc == 'localhost':
        # According to RFC 8089, same as empty authority.
        netloc = ''
    elif sys.platform == 'win32':
        # If we have a UNC path, prepend UNC share notation.
        netloc = '\\\\' + netloc
    else:
        raise ValueError(
            'non-local file URIs are not supported on this platform: %r'
            % url
        )

    path = urllib_request.url2pathname(netloc + path)
    return path

def is_dir_url(link):
    # type: (Link) -> bool
    """Return whether a file:// Link points to a directory.

    ``link`` must not have any other scheme but file://. Call is_file_url()
    first.

    """
    link_path = url_to_path(link.url_without_fragment)
    return os.path.isdir(link_path)


def _copy_file(filename, location, link):
    copy = True
    download_location = os.path.join(location, link.filename)
    if os.path.exists(download_location):
        response = ask_path_exists(
            'The file %s exists. (i)gnore, (w)ipe, (b)ackup, (a)abort' %
            display_path(download_location), ('i', 'w', 'b', 'a'))
        if response == 'i':
            copy = False
        elif response == 'w':
            logger.warning('Deleting %s', display_path(download_location))
            os.remove(download_location)
        elif response == 'b':
            dest_file = backup_dir(download_location)
            logger.warning(
                'Backing up %s to %s',
                display_path(download_location),
                display_path(dest_file),
            )
            shutil.move(download_location, dest_file)
        elif response == 'a':
            sys.exit(-1)
    if copy:
        shutil.copy(filename, download_location)
        logger.info('Saved %s', display_path(download_location))

def _check_download_dir(link, download_dir, hashes):
    # type: (Link, str, Optional[Hashes]) -> Optional[str]
    """ Check download_dir for previously downloaded file with correct hash
        If a correct file is found return its path else None
    """
    download_path = os.path.join(download_dir, link.filename)
    if os.path.exists(download_path):
        # If already downloaded, does its hash match?
        logger.info('File was already downloaded %s', download_path)
        if hashes:
            try:
                hashes.check_against_path(download_path)
            except HashMismatch:
                logger.warning(
                    'Previously-downloaded file %s has bad hash. '
                    'Re-downloading.',
                    download_path
                )
                os.unlink(download_path)
                return None
        return download_path
    return None


def unpack_file_url(
    link,  # type: Link
    location,  # type: str
    download_dir=None,  # type: Optional[str]
    hashes=None  # type: Optional[Hashes]
):
    # type: (...) -> None
    """Unpack link into location.

    If download_dir is provided and link points to a file, make a copy
    of the link file inside download_dir.
    """

    link_path = url_to_path(link.url_without_fragment)
    # If it's a url to a local directory
    if is_dir_url(link):

        def ignore(d, names):
            # Pulling in those directories can potentially be very slow,
            # exclude the following directories if they appear in the top
            # level dir (and only it).
            # See discussion at https://github.com/pypa/pip/pull/6770
            return ['.tox', '.nox'] if d == link_path else []

        if os.path.isdir(location):
            rmtree(location)
        shutil.copytree(link_path,
                        location,
                        symlinks=True,
                        ignore=ignore)

        if download_dir:
            logger.info('Link is a directory, ignoring download_dir')
        return

    # If --require-hashes is off, `hashes` is either empty, the
    # link's embedded hash, or MissingHashes; it is required to
    # match. If --require-hashes is on, we are satisfied by any
    # hash in `hashes` matching: a URL-based or an option-based
    # one; no internet-sourced hash will be in `hashes`.
    if hashes:
        hashes.check_against_path(link_path)

    # If a download dir is specified, is the file already there and valid?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link,
                                                      download_dir,
                                                      hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
    else:
        from_path = link_path

    content_type = mimetypes.guess_type(from_path)[0]

    # unpack the archive to the build dir location. even when only downloading
    # archives, they have to be unpacked to parse dependencies
    unpack_file(from_path, location, content_type, link)

    # a download dir is specified and not already downloaded
    if download_dir and not already_downloaded_path:
        _copy_file(from_path, download_dir, link)

