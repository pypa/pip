from pip._internal.utils.typing import MYPY_CHECK_RUNNING


if MYPY_CHECK_RUNNING:
    from typing import Any, List, Sequence, Union
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from .candidates import Candidate
    from .requirements import Requirement, ResolveOptions

    Dependency = Union[Requirement, Candidate]


class Provider(object):
    def __init__(
        self,
        finder,     # type: PackageFinder
        preparer,   # type: RequirementPreparer
        options,    # type: ResolveOptions
    ):
        # type: (...) -> None
        super(Provider, self).__init__()
        self.finder = finder
        self.preparer = preparer
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

    def get_dependencies(self, candidate):
        # type: (Candidate) -> Sequence[Requirement]
        return candidate.get_dependencies()
