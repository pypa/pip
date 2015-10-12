from __future__ import absolute_import

import hashlib
import logging
import sys

from pip.basecommand import Command
from pip.exceptions import FAVORITE_HASH
from pip.status_codes import ERROR
from pip.utils import read_chunks


logger = logging.getLogger(__name__)


class HashCommand(Command):
    """
    Compute a hash of a local package archive.

    These can be used with --hash in a requirements file to do repeatable
    installs.

    """
    name = 'hash'
    usage = """%prog [options] <file> ..."""
    summary = 'Compute hashes of package archives.'

    def run(self, options, args):
        if not args:
            self.parser.print_usage(sys.stderr)
            return ERROR

        for path in args:
            logger.info('%s:\n--hash=%s:%s' % (path,
                                               FAVORITE_HASH,
                                               _hash_of_file(path)))


def _hash_of_file(path):
    """Return the hash digest of a file."""
    with open(path, 'rb') as archive:
        hash = hashlib.new(FAVORITE_HASH)
        for chunk in read_chunks(archive):
            hash.update(chunk)
    return hash.hexdigest()
