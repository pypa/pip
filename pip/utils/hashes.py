from __future__ import absolute_import

import hashlib

from pip.exceptions import (HashMismatch, HashMissing, InstallationError,
                            FAVORITE_HASH)
from pip._vendor.six import iteritems, iterkeys, itervalues


class Hashes(object):
    """A wrapper that builds multiple hashes at once and checks them against
    known-good values

    """
    def __init__(self, hashes=None):
        """
        :param hashes: A dict of algorithm names pointing to lists of allowed
            hex digests
        """
        self._goods = {} if hashes is None else hashes

    def check_against_chunks(self, chunks):
        """Check good hashes against ones built from iterable of chunks of
        data.

        Raise HashMismatch if none match.

        """
        gots = {}
        for hash_name in iterkeys(self._goods):
            try:
                gots[hash_name] = hashlib.new(hash_name)
            except (ValueError, TypeError):
                raise InstallationError('Unknown hash name: %s' % hash_name)

        for chunk in chunks:
            for hash in itervalues(gots):
                hash.update(chunk)

        for hash_name, got in iteritems(gots):
            if got.hexdigest() in self._goods[hash_name]:
                return
        self._raise(gots)

    def _raise(self, gots):
        raise HashMismatch(self._goods, gots)

    def check_against_file(self, file):
        """Check good hashes against a file-like object

        Raise HashMismatch if none match.

        """
        def chunks():
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                yield chunk
        return self.check_against_chunks(chunks())

    def check_against_path(self, path):
        with open(path, 'rb') as file:
            return self.check_against_file(file)

    def __nonzero__(self):
        """Return whether I know any known-good hashes."""
        return bool(self._goods)

    def __bool__(self):
        return self.__nonzero__()


class MissingHashes(Hashes):
    """A workalike for Hashes used when we're missing a hash for a requirement

    It computes the "gotten" hash of the requirement and raises a HashMissing
    exception showing it to the user.

    """
    def __init__(self):
        """Don't offer the ``hashes`` kwarg."""
        # Pass our favorite hash in to generate a "gotten hash". With the
        # empty list, it will never match, so an error will always raise.
        super(MissingHashes, self).__init__(hashes={FAVORITE_HASH: []})

    def _raise(self, gots):
        raise HashMissing(gots[FAVORITE_HASH].hexdigest())
