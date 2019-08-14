import mimetypes
import os
import shutil

from pip._internal.utils.misc import rmtree
from pip._internal.utils.unpacking import logger, unpack_file


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
    from pip._internal.download import (
        is_dir_url,
        url_to_path,
        _check_download_dir,
        _copy_file
    )

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