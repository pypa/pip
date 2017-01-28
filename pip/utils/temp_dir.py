from __future__ import absolute_import

import os.path
import tempfile

from pip.utils import rmtree


class TempDirectory(object):
    """A Helper class that owns and cleans up a temporary directory.
    """

    def __init__(self, path=None, delete=None, type="temp"):
        if path is None:
            # We realpath here because some systems have their default tmpdir
            # symlinked to another directory.  This tends to confuse build
            # scripts, so we canonicalize the path by traversing potential
            # symlinks here.
            path = os.path.realpath(
                tempfile.mkdtemp(prefix="pip-", suffix="-" + type)
            )
            # If we were not given an explicit directory, and we were not given
            # an explicit delete option, then we'll default to deleting.
            if delete is None:
                delete = True

        self.path = path
        self.delete = delete

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.path)

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        if self.delete:
            self.cleanup()

    def cleanup(self):
        rmtree(self.path)
