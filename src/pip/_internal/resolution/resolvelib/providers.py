from pip._internal.resolution.legacy.resolver import (
    # TODO: Re-implement me.
    InstallRequirementProvider,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import RemoteCandidate
from .requirements import DirectRequirement, VersionedRequirement


if MYPY_CHECK_RUNNING:
    from typing import Any, List, Sequence, Union

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement

    from .candidates import Candidate
    from .requirements import Requirement, ResolveOptions

    Dependency = Union[Requirement, Candidate]


class Provider(object):
    def __init__(
        self,
        finder,     # type: PackageFinder
        preparer,   # type: RequirementPreparer
        make_ireq,  # type: InstallRequirementProvider
        options,    # type: ResolveOptions
    ):
        # type: (...) -> None
        super(Provider, self).__init__()
        self.finder = finder
        self.preparer = preparer
        self.make_ireq = make_ireq
        self.options = options

    def identify(self, dependency):
        # type: (Dependency) -> str
        return dependency.name

    def get_preference(self, resolution, candidates, information):
        # type: (Any, List[Candidate], Any) -> int
        return len(candidates)

    def find_matches(self, req):
        # type: (Requirement) -> Sequence[Candidate]
        return req.find_matches(
            self.finder,
            self.preparer,
            self.options,
        )

    def is_satisfied_by(self, requirement, candidate):
        # type: (Requirement, Candidate) -> bool
        return requirement.is_satisfied_by(candidate)

    def _requirement_from_spec(self, spec, parent):
        # type: (str, InstallRequirement) -> Requirement
        ireq = self.make_ireq(spec, parent)
        if ireq.link is None:
            return VersionedRequirement(ireq)
        dist = self.preparer.prepare_linked_requirement(ireq)
        cand = RemoteCandidate(ireq, dist.get_pkg_resources_distribution())
        return DirectRequirement(cand)

    def get_dependencies(self, candidate):
        # type: (Candidate) -> Sequence[Requirement]
        return candidate.get_dependencies(self._requirement_from_spec)
