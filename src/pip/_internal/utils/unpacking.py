# mypy: strict-optional=False

import logging
import os
import shutil
import stat
import tarfile
import zipfile
import mimetypes

from pip._internal.download import url_to_path, is_dir_url, _check_download_dir, _copy_file
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.exceptions import InstallationError

from pip._internal.utils.misc import (
    rmtree,
    ensure_dir,
    has_leading_dir,
    current_umask,
    split_leading_dir,
    is_svn_page,
    file_contents
)

if MYPY_CHECK_RUNNING:
    from typing import Optional
    from pip._internal.models.link import Link
    from pip._internal.utils.hashes import Hashes

logger = logging.getLogger(__name__)

WHEEL_EXTENSION = '.whl'
BZ2_EXTENSIONS = ('.tar.bz2', '.tbz')
XZ_EXTENSIONS = ('.tar.xz', '.txz', '.tlz', '.tar.lz', '.tar.lzma')
ZIP_EXTENSIONS = ('.zip', WHEEL_EXTENSION)
TAR_EXTENSIONS = ('.tar.gz', '.tgz', '.tar')
ARCHIVE_EXTENSIONS = (
    ZIP_EXTENSIONS + BZ2_EXTENSIONS + TAR_EXTENSIONS + XZ_EXTENSIONS)
SUPPORTED_EXTENSIONS = ZIP_EXTENSIONS + TAR_EXTENSIONS

try:
    import bz2  # noqa
    SUPPORTED_EXTENSIONS += BZ2_EXTENSIONS
except ImportError:
    logger.debug('bz2 module is not available')

try:
    # Only for Python 3.3+
    import lzma  # noqa
    SUPPORTED_EXTENSIONS += XZ_EXTENSIONS
except ImportError:
    logger.debug('lzma module is not available')


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


def unzip_file(filename, location, flatten=True):
    # type: (str, str, bool) -> None
    """
    Unzip the file (with path `filename`) to the destination `location`.  All
    files are written based on system defaults and umask (i.e. permissions are
    not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written. Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    zipfp = open(filename, 'rb')
    try:
        zip = zipfile.ZipFile(zipfp, allowZip64=True)
        leading = has_leading_dir(zip.namelist()) and flatten
        for info in zip.infolist():
            name = info.filename
            fn = name
            if leading:
                fn = split_leading_dir(name)[1]
            fn = os.path.join(location, fn)
            dir = os.path.dirname(fn)
            if fn.endswith('/') or fn.endswith('\\'):
                # A directory
                ensure_dir(fn)
            else:
                ensure_dir(dir)
                # Don't use read() to avoid allocating an arbitrarily large
                # chunk of memory for the file's content
                fp = zip.open(name)
                try:
                    with open(fn, 'wb') as destfp:
                        shutil.copyfileobj(fp, destfp)
                finally:
                    fp.close()
                    mode = info.external_attr >> 16
                    # if mode and regular file and any execute permissions for
                    # user/group/world?
                    if mode and stat.S_ISREG(mode) and mode & 0o111:
                        # make dest file have execute for user/group/world
                        # (chmod +x) no-op on windows per python docs
                        os.chmod(fn, (0o777 - current_umask() | 0o111))
    finally:
        zipfp.close()


def untar_file(filename, location):
    # type: (str, str) -> None
    """
    Untar the file (with path `filename`) to the destination `location`.
    All files are written based on system defaults and umask (i.e. permissions
    are not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written.  Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    if filename.lower().endswith('.gz') or filename.lower().endswith('.tgz'):
        mode = 'r:gz'
    elif filename.lower().endswith(BZ2_EXTENSIONS):
        mode = 'r:bz2'
    elif filename.lower().endswith(XZ_EXTENSIONS):
        mode = 'r:xz'
    elif filename.lower().endswith('.tar'):
        mode = 'r'
    else:
        logger.warning(
            'Cannot determine compression type for file %s', filename,
        )
        mode = 'r:*'
    tar = tarfile.open(filename, mode)
    try:
        leading = has_leading_dir([
            member.name for member in tar.getmembers()
        ])
        for member in tar.getmembers():
            fn = member.name
            if leading:
                # https://github.com/python/mypy/issues/1174
                fn = split_leading_dir(fn)[1]  # type: ignore
            path = os.path.join(location, fn)
            if member.isdir():
                ensure_dir(path)
            elif member.issym():
                try:
                    # https://github.com/python/typeshed/issues/2673
                    tar._extract_member(member, path)  # type: ignore
                except Exception as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    logger.warning(
                        'In the tar file %s the member %s is invalid: %s',
                        filename, member.name, exc,
                    )
                    continue
            else:
                try:
                    fp = tar.extractfile(member)
                except (KeyError, AttributeError) as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    logger.warning(
                        'In the tar file %s the member %s is invalid: %s',
                        filename, member.name, exc,
                    )
                    continue
                ensure_dir(os.path.dirname(path))
                with open(path, 'wb') as destfp:
                    shutil.copyfileobj(fp, destfp)
                fp.close()
                # Update the timestamp (useful for cython compiled files)
                # https://github.com/python/typeshed/issues/2673
                tar.utime(member, path)  # type: ignore
                # member have any execute permissions for user/group/world?
                if member.mode & 0o111:
                    # make dest file have execute for user/group/world
                    # no-op on windows per python docs
                    os.chmod(path, (0o777 - current_umask() | 0o111))
    finally:
        tar.close()


def unpack_file(
    filename,  # type: str
    location,  # type: str
    content_type,  # type: Optional[str]
    link  # type: Optional[Link]
):
    # type: (...) -> None
    filename = os.path.realpath(filename)
    if (content_type == 'application/zip' or
            filename.lower().endswith(ZIP_EXTENSIONS) or
            zipfile.is_zipfile(filename)):
        unzip_file(
            filename,
            location,
            flatten=not filename.endswith('.whl')
        )
    elif (content_type == 'application/x-gzip' or
            tarfile.is_tarfile(filename) or
            filename.lower().endswith(
                TAR_EXTENSIONS + BZ2_EXTENSIONS + XZ_EXTENSIONS)):
        untar_file(filename, location)
    elif (content_type and content_type.startswith('text/html') and
            is_svn_page(file_contents(filename))):
        # We don't really care about this
        from pip._internal.vcs.subversion import Subversion
        url = 'svn+' + link.url
        Subversion().unpack(location, url=url)
    else:
        # FIXME: handle?
        # FIXME: magic signatures?
        logger.critical(
            'Cannot unpack file %s (downloaded from %s, content-type: %s); '
            'cannot detect archive format',
            filename, location, content_type,
        )
        raise InstallationError(
            'Cannot determine archive format of %s' % location
        )


