from __future__ import absolute_import

import os.path
import tempfile

from pip.utils import rmtree


class RequirementCache(object):

    def __init__(self, path=None, delete=None):
        # If we were not given an explicit directory, and we were not given an
        # explicit delete option, then we'll default to deleting.
        if path is None and delete is None:
            delete = True
        self._path = path

        self.path = None
        self.delete = delete

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
