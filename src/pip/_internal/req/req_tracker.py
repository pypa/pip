# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

from __future__ import absolute_import

import contextlib
import errno
import hashlib
import logging
import os

from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from types import TracebackType
    from typing import Iterator, Optional, Set, Type
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.models.link import Link

logger = logging.getLogger(__name__)


class RequirementTracker(object):

    def __init__(self):
        # type: () -> None
        self._root = os.environ.get('PIP_REQ_TRACKER')
        if self._root is None:
            self._temp_dir = TempDirectory(delete=False, kind='req-tracker')
            self._root = os.environ['PIP_REQ_TRACKER'] = self._temp_dir.path
            logger.debug('Created requirements tracker %r', self._root)
        else:
            self._temp_dir = None
            logger.debug('Re-using requirements tracker %r', self._root)
        self._entries = set()  # type: Set[InstallRequirement]

    def __enter__(self):
        # type: () -> RequirementTracker
        return self

    def __exit__(
        self,
        exc_type,  # type: Optional[Type[BaseException]]
        exc_val,  # type: Optional[BaseException]
        exc_tb  # type: Optional[TracebackType]
    ):
        # type: (...) -> None
        self.cleanup()

    def _entry_path(self, link):
        # type: (Link) -> str
        hashed = hashlib.sha224(link.url_without_fragment.encode()).hexdigest()
        return os.path.join(self._root, hashed)

    def add(self, req):
        # type: (InstallRequirement) -> None
        """Add an InstallRequirement to build tracking.
        """

        # Get the file to write information about this requirement.
        entry_path = self._entry_path(req.link)

        # Try reading from the file. If it exists and can be read from, a build
        # is already in progress, so a LookupError is raised.
        try:
            with open(entry_path) as fp:
                contents = fp.read()
        except IOError as e:
            # if the error is anything other than "file does not exist", raise.
            if e.errno != errno.ENOENT:
                raise
        else:
            message = '%s is already being built: %s' % (req.link, contents)
            raise LookupError(message)

        # If we're here, req should really not be building already.
        assert req not in self._entries

        # Start tracking this requirement.
        with open(entry_path, 'w') as fp:
            fp.write(str(req))
        self._entries.add(req)

        logger.debug('Added %s to build tracker %r', req, self._root)

    def remove(self, req):
        # type: (InstallRequirement) -> None
        """Remove an InstallRequirement from build tracking.
        """

        # Delete the created file and the corresponding entries.
        os.unlink(self._entry_path(req.link))
        self._entries.remove(req)

        logger.debug('Removed %s from build tracker %r', req, self._root)

    def cleanup(self):
        # type: () -> None
        for req in set(self._entries):
            self.remove(req)

        if self._temp_dir is None:
            # Did not setup the directory. No action needed.
            logger.debug("Cleaned build tracker: %r", self._root)
            return

        # Cleanup the directory.
        self._temp_dir.cleanup()
        logger.debug("Removed build tracker: %r", self._root)

    @contextlib.contextmanager
    def track(self, req):
        # type: (InstallRequirement) -> Iterator[None]
        self.add(req)
        yield
        self.remove(req)
