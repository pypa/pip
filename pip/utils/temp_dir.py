from __future__ import absolute_import

import logging
import os.path
import tempfile

from pip.utils import rmtree


logger = logging.getLogger(__name__)


class TempDirectory(object):
    """Helper class that owns and cleans up a temporary directory.
    """

    def __init__(self, path=None, delete=None, kind="temp"):
        super(TempDirectory, self).__init__()

        if path is None and delete is None:
            # If we were not given an explicit directory, and we were not given
            # an explicit delete option, then we'll default to deleting.
            delete = True

        self.path = path
        self.delete = delete
        self.kind = kind

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.path)

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc, value, tb):
        if self.delete:
            self.cleanup()

    def create(self):
        if self.path is not None:
            logger.debug(
                "Skipped creation of temporary directory: {}".format(self.path)
            )
            return
        # We realpath here because some systems have their default tmpdir
        # symlinked to another directory.  This tends to confuse build
        # scripts, so we canonicalize the path by traversing potential
        # symlinks here.
        self.path = os.path.realpath(
            tempfile.mkdtemp(prefix="pip-{}-".format(self.kind))
        )
        logger.debug("Created temporary directory: {}".format(self.path))

    def cleanup(self):
        if self.path is not None and os.path.exists(self.path):
            rmtree(self.path)
        self.path = None
