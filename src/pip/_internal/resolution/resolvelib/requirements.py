from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import ConcreteCandidate, ExtrasCandidate, format_name

if MYPY_CHECK_RUNNING:
    from typing import Sequence
    from pip._vendor.packaging.requirements import (
        Requirement as PEP440Requirement,
    )
    from .candidates import Candidate


class Requirement(object):
    @property
    def name(self):
        # type: () -> str
        raise NotImplementedError("Subclass should override")

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        raise NotImplementedError("Subclass should override")

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return False


class DirectRequirement(Requirement):
    def __init__(self, candidate):
        # type: (Candidate) -> None
        self._candidate = candidate

    @property
    def name(self):
        # type: () -> str
        return self._candidate.name

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        return [self._candidate]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate.same_as(self._candidate)


class VersionedRequirement(Requirement):
    def __init__(self, requirement):
        # type: (PEP440Requirement) -> None
        assert requirement.url is None, "direct reference not allowed"
        self._req = requirement

    @property
    def name(self):
        # type: () -> str
        return format_name(canonicalize_name(self._req.name), self._req.extras)

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        # TODO: Implement finding candidates from index etc.
        candidates = []  # type: Sequence[ConcreteCandidate]
        if not self._req.extras:
            return candidates
        return [ExtrasCandidate(c, self._req.extras) for c in candidates]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return (
            candidate.name == self.name and
            candidate.version in self._req.specifier
        )
