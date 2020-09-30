from pip._vendor.six.moves import collections_abc  # type: ignore

from pip._internal.utils.compat import lru_cache
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, Iterator, Optional, Set

    from pip._vendor.packaging.version import _BaseVersion

    from .base import Candidate


class _InstalledFirstCandidatesIterator(collections_abc.Iterator):
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers to keep the version of an
    already-installed package. The already-installed candidate is always
    returned first. Candidates from index are accessed only when the resolver
    wants them, and the already-installed version is excluded from them.
    """
    def __init__(
        self,
        get_others,  # type: Callable[[], Iterator[Candidate]]
        installed,  # type: Optional[Candidate]
    ):
        self._installed = installed
        self._get_others = get_others
        self._others = None  # type: Optional[Iterator[Candidate]]
        self._returned = set()  # type: Set[_BaseVersion]

    def __next__(self):
        # type: () -> Candidate
        if self._installed and self._installed.version not in self._returned:
            self._returned.add(self._installed.version)
            return self._installed
        if self._others is None:
            self._others = self._get_others()
        cand = next(self._others)
        while cand.version in self._returned:
            cand = next(self._others)
        self._returned.add(cand.version)
        return cand

    next = __next__  # XXX: Python 2.


class _InstalledReplacesCandidatesIterator(collections_abc.Iterator):
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers to upgrade an
    already-installed package. Candidates from index are returned in their
    normal ordering, except replaced when the version is already installed.
    """
    def __init__(
        self,
        get_others,  # type: Callable[[], Iterator[Candidate]]
        installed,  # type: Optional[Candidate]
    ):
        self._installed = installed
        self._get_others = get_others
        self._others = None  # type: Optional[Iterator[Candidate]]
        self._returned = set()  # type: Set[_BaseVersion]

    def __next__(self):
        # type: () -> Candidate
        if self._others is None:
            self._others = self._get_others()
        try:
            cand = next(self._others)
            while cand.version in self._returned:
                cand = next(self._others)
            if self._installed and cand.version == self._installed.version:
                cand = self._installed
        except StopIteration:
            # Return the already-installed candidate as the last item if its
            # version does not exist on the index.
            if not self._installed:
                raise
            if self._installed.version in self._returned:
                raise
            cand = self._installed
        self._returned.add(cand.version)
        return cand

    next = __next__  # XXX: Python 2.


class FoundCandidates(collections_abc.Sequence):
    """A lazy sequence to provide candidates to the resolver.

    The intended usage is to return this from `find_matches()` so the resolver
    can iterate through the sequence multiple times, but only access the index
    page when remote packages are actually needed. This improve performances
    when suitable candidates are already installed on disk.
    """
    def __init__(
        self,
        get_others,  # type: Callable[[], Iterator[Candidate]]
        installed,  # type: Optional[Candidate]
        prefers_installed,  # type: bool
    ):
        self._get_others = get_others
        self._installed = installed
        self._prefers_installed = prefers_installed

    def __getitem__(self, index):
        # type: (int) -> Candidate
        # Implemented to satisfy the ABC check, This is not needed by the
        # resolver, and should not be used by the provider either (for
        # performance reasons).
        raise NotImplementedError("don't do this")

    def __iter__(self):
        # type: () -> Iterator[Candidate]
        if self._prefers_installed:
            klass = _InstalledFirstCandidatesIterator
        else:
            klass = _InstalledReplacesCandidatesIterator
        return klass(self._get_others, self._installed)

    @lru_cache(maxsize=1)
    def __len__(self):
        # type: () -> int
        return sum(1 for _ in self)

    @lru_cache(maxsize=1)
    def __bool__(self):
        # type: () -> bool
        if self._prefers_installed and self._installed:
            return True
        return any(self)

    __nonzero__ = __bool__  # XXX: Python 2.
