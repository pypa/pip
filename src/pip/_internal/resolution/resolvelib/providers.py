from pip._vendor.packaging.requirements import Requirement as PEP440Requirement
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.resolvelib.models import (
    DirectCandidate,
    EditableCandidate,
    EditableRequirement,
    ExtrasCandidate,
    SingleCandidateRequirement,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, List, Mapping, Optional, Sequence, Union
    from pip._internal.cache import WheelCache
    from pip._internal.distributions import AbstractDistribution
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.resolution.resolvelib.models import BareCandidate

    Requirement = Union[
        EditableRequirement,
        PEP440Requirement,
        SingleCandidateRequirement,
    ]
    Candidate = Union[BareCandidate, ExtrasCandidate]
    Dependency = Union[Requirement, Candidate]


class _DistributionBuilder(object):
    def __init__(
        self,
        preparer,     # type: RequirementPreparer
        isolated,     # type: bool
        pep517,       # type: bool
        wheel_cache,  # type: Optional[WheelCache]
    ):
        # type: (...) -> None
        self.preparer = preparer
        self.isolated = isolated
        self.pep517 = pep517
        self.wheel_cache = wheel_cache
        self._built = {}  # type: Mapping[str, AbstractDistribution]

    def get_pep440_dist(self, requirement):
        # type: (PEP440Requirement) -> AbstractDistribution
        key = str(requirement)
        if key in self._built:
            return self._built[key]
        ireq = InstallRequirement(
            requirement,
            comes_from=None,  # TODO: Supply this.
            isolated=self.isolated,
            use_pep517=self.pep517,
            wheel_cache=self.wheel_cache,
        )
        ireq  # TODO: Make this linked and call prepare...
        raise NotImplementedError()


class Provider(object):
    def __init__(self, finder, preparer):
        # type: (PackageFinder, RequirementPreparer) -> None
        super(Provider, self).__init__()
        self.finder = finder
        self.preparer = preparer

    def identify(self, dependency):
        # type: (Dependency) -> str
        return canonicalize_name(dependency.name)

    def get_preference(self, resolution, candidates, information):
        # type: (Any, List[Candidate], Any) -> int
        return len(candidates)

    def _find_candidates(self, req):
        # type: (PEP440Requirement) -> List[BareCandidate]
        found = self.finder.find_best_candidate(
            # TODO: Implement hash mode.
            req.name, req.specifier, hashes=None,
        )
        return list(found.iter_applicable())

    def _find_editable_candidate(self, req):
        # type: (EditableRequirement) -> EditableCandidate
        raise NotImplementedError()

    def find_matches(self, req):
        # type: (Requirement) -> Sequence[Candidate]
        candidates = []  # type: List[BareCandidate]
        if isinstance(req, SingleCandidateRequirement):
            candidates = [req.candidate]
        elif isinstance(req, EditableRequirement):
            candidates = [self._find_editable_candidate(req)]
        elif req.url:
            candidates = [DirectCandidate(req.name, req.url)]
        else:
            candidates = self._find_candidates(req)
        if req.extras:
            return [ExtrasCandidate(c, req.extras) for c in candidates]
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        # type: (Requirement, Candidate) -> bool
        if requirement.url:
            # TODO: Handle candidates without link (not attribute or is None).
            return candidate.link.url == requirement.url
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        # type: (Candidate) -> List[Requirement]
        # TODO: Implement me.
        raise NotImplementedError()
