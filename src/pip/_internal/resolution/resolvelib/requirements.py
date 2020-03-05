from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import ExtrasCandidate, NamedCandidate, format_name

if MYPY_CHECK_RUNNING:
    from typing import Sequence
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.req.req_install import InstallRequirement
    from .candidates import Candidate, ConcreteCandidate


class Requirement(object):
    @property
    def name(self):
        # type: () -> str
        raise NotImplementedError("Subclass should override")

    def find_matches(self, finder):
        # type: (PackageFinder) -> Sequence[Candidate]
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

    def find_matches(self, finder):
        # type: (PackageFinder) -> Sequence[Candidate]
        return [self._candidate]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate.same_as(self._candidate)


class VersionedRequirement(Requirement):
    def __init__(self, ireq):
        # type: (InstallRequirement) -> None
        assert ireq.req is not None, "Un-prepared requirement not allowed"
        assert ireq.req.url is None, "direct reference not allowed"
        self._ireq = ireq

    @property
    def name(self):
        # type: () -> str
        canonical_name = canonicalize_name(self._ireq.req.name)
        return format_name(canonical_name, self._ireq.req.extras)

    def find_matches(self, finder):
        # type: (PackageFinder) -> Sequence[Candidate]
        found = finder.find_best_candidate(
            project_name=self._ireq.req.name,
            specifier=self._ireq.req.specifier,
            hashes=self._ireq.hashes(trust_internet=False),
        )
        candidates = [
            NamedCandidate(
                name=ican.name,
                version=ican.version,
                link=ican.link,
            )
            for ican in found.iter_applicable()
        ]  # type: Sequence[ConcreteCandidate]
        if not self._ireq.req.extras:
            return candidates
        return [ExtrasCandidate(c, self._ireq.req.extras) for c in candidates]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return (
            candidate.name == self.name and
            candidate.version in self._ireq.req.specifier
        )
