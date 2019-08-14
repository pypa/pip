# mypy: strict-optional=False

from __future__ import absolute_import

import logging
import os
import shutil
import stat
import tarfile
import zipfile

from pip._internal.exceptions import InstallationError
from pip._internal.utils.misc import (
    current_umask,
    ensure_dir,
    file_contents,
    has_leading_dir,
    is_svn_page,
    split_leading_dir,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional
    from pip._internal.models.link import Link

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
