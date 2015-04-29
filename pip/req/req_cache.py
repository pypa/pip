from __future__ import absolute_import

import os.path
import tempfile

from pip.utils import rmtree


class RequirementCache(object):

    def __init__(self, path=None, delete=None, src_dir=None):
        """Create a RequirementCache.

        :param path: The path to store working data - wheels, sdists, etc. If
            None then a temp dir will be made on __enter__.
        :param delete: If False then path will not be deleted on __exit__.
            If None, then path will be deleted on __exit__ only if path was
            None. If True then path will be deleted on __exit__.
        :param src_dir: The parent path that editable requirements will
            be checked out under. Will be created on demand if needed.
        """
        # If we were not given an explicit directory, and we were not given an
        # explicit delete option, then we'll default to deleting.
        if path is None and delete is None:
            delete = True
        self._path = path

        self.path = None
        self.delete = delete
        self.src_dir = os.path.abspath(src_dir) if src_dir else None

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.path)

    def __enter__(self):
        if self._path is None:
            # We realpath here because some systems have their default tmpdir
            # symlinked to another directory.  This tends to confuse build
            # scripts, so we canonicalize the path by traversing potential
            # symlinks here.
            self.path = os.path.realpath(tempfile.mkdtemp(prefix="pip-build-"))
            # If we were not given an explicit directory, and we were not given
            # an explicit delete option, then we'll default to deleting.
            if self.delete is None:
                self.delete = True
        else:
            self.path = self._path
        return self

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.delete:
            rmtree(self.path)
        self.path = None
