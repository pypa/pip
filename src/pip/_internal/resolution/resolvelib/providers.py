from pip._vendor.packaging.requirements import (
    Requirement as PEP440Requirement,
)
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.resolution.resolvelib.models import (
    DirectCandidate,
    ExtrasCandidate,
    SingleCandidateRequirement,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, List, Union, Sized
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.models.candidate import InstallationCandidate
    from pip._internal.operations.prepare import RequirementPreparer

    Requirement = Union[PEP440Requirement, SingleCandidateRequirement]
    Candidate = Union[InstallationCandidate, DirectCandidate, ExtrasCandidate]
    Dependency = Union[Requirement, Candidate]


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
        # type: (Any, Sized[Candidate], Any) -> int
        return len(candidates)

    def _find_candidates(self, req):
        # type: (Requirement) -> List[Candidate]
        candidates = self.finder.find_all_candidates(req.name)
        evaluator = self.finder.make_candidate_evaluator(
            project_name=req.name,
            speficier=req.specifier,
            hashes=None,  # TODO: Implement hash mode.
        )
        return evaluator.sort_applicable_candidates(candidates)

    def find_matches(self, req):
        # type: (Requirement) -> List[Candidate]
        if isinstance(req, SingleCandidateRequirement):
            return [req.candidate]

        if req.url:
            candidates = [DirectCandidate(req.name, req.url)]
        else:
            candidates = self._find_candidates(req)

        if req.extras:
            candidates = [ExtrasCandidate(c, req.extras) for c in candidates]

        return candidates

    def is_satisfied_by(self, requirement, candidate):
        # type: (Requirement, Candidate) -> bool
        if requirement.url:
            return candidate.link.url == requirement.url
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        # type: (Candidate) -> List[Requirement]
        # TODO: Implement me.
        raise NotImplementedError()
