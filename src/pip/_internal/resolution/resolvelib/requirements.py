from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import Requirement, format_name

if MYPY_CHECK_RUNNING:
    from typing import Sequence

    from pip._internal.req.req_install import InstallRequirement

    from .base import Candidate
    from .factory import Factory


class ExplicitRequirement(Requirement):
    def __init__(self, candidate):
        # type: (Candidate) -> None
        self.candidate = candidate

    @property
    def name(self):
        # type: () -> str
        # No need to canonicalise - the candidate did this
        return self.candidate.name

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        return [self.candidate]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate == self.candidate


class NoMatchRequirement(Requirement):
    """A requirement that never matches anything.

    Note: Similar to ExplicitRequirement, the caller should handle name
    canonicalisation; this class does not perform it.
    """
    def __init__(self, name):
        # type: (str) -> None
        self._name = name

    @property
    def name(self):
        # type: () -> str
        return self._name

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        return []

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return False


class SpecifierRequirement(Requirement):
    def __init__(self, ireq, factory):
        # type: (InstallRequirement, Factory) -> None
        assert ireq.link is None, "This is a link, not a specifier"
        self._ireq = ireq
        self._factory = factory
        self.extras = ireq.req.extras

    @property
    def name(self):
        # type: () -> str
        canonical_name = canonicalize_name(self._ireq.req.name)
        return format_name(canonical_name, self.extras)

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        found = self._factory.finder.find_best_candidate(
            project_name=self._ireq.req.name,
            specifier=self._ireq.req.specifier,
            hashes=self._ireq.hashes(trust_internet=False),
        )
        return [
            self._factory.make_candidate_from_ican(
                ican=ican,
                extras=self.extras,
                parent=self._ireq,
            )
            for ican in found.iter_applicable()
        ]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        assert candidate.name == self.name, \
            "Internal issue: Candidate is not for this requirement " \
            " {} vs {}".format(candidate.name, self.name)
        return candidate.version in self._ireq.req.specifier
