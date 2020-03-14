from pip._vendor.resolvelib import BaseReporter
from pip._vendor.resolvelib import Resolver as RLResolver

from pip._internal.resolution.base import BaseResolver
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Dict, List, Optional, Tuple

    from pip._vendor.resolvelib.resolvers import Result

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.req.req_set import RequirementSet
    from pip._internal.resolution.base import InstallRequirementProvider

    from .base import Candidate, Requirement


# FIXME: Import the actual implementation.
# This is a stub to pass typing checks.
class PipProvider(object):
    def __init__(
        self,
        finder,  # type: PackageFinder
        preparer,  # type: RequirementPreparer
        make_install_req,  # type: InstallRequirementProvider
    ):
        # type: (...) -> None
        super(PipProvider, self).__init__()

    def make_requirement(self, r):
        # type: (InstallRequirement) -> Requirement
        raise NotImplementedError()

    def get_install_requirement(self, c):
        # type: (Candidate) -> InstallRequirement
        raise NotImplementedError()


class Resolver(BaseResolver):
    def __init__(
        self,
        preparer,  # type: RequirementPreparer
        finder,  # type: PackageFinder
        make_install_req,  # type: InstallRequirementProvider
        use_user_site,  # type: bool
        ignore_dependencies,  # type: bool
        ignore_installed,  # type: bool
        ignore_requires_python,  # type: bool
        force_reinstall,  # type: bool
        upgrade_strategy,  # type: str
        py_version_info=None,  # type: Optional[Tuple[int, ...]]
    ):
        super(Resolver, self).__init__()
        self.finder = finder
        self.preparer = preparer
        self.make_install_req = make_install_req
        self._result = None  # type: Optional[Result]

    def resolve(self, root_reqs, check_supported_wheels):
        # type: (List[InstallRequirement], bool) -> RequirementSet
        provider = PipProvider(
            self.finder,
            self.preparer,
            self.make_install_req,
        )
        reporter = BaseReporter()
        resolver = RLResolver(provider, reporter)

        requirements = [provider.make_requirement(r) for r in root_reqs]
        self._result = resolver.resolve(requirements)

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for candidate in self._result.mapping.values():
            ireq = provider.get_install_requirement(candidate)
            req_set.add_named_requirement(ireq)

        return req_set

    def get_installation_order(self, req_set):
        # type: (RequirementSet) -> List[InstallRequirement]
        """Create a list that orders given requirements for installation.

        The returned list should contain all requirements in ``req_set``,
        so the caller can loop through it and have a requirement installed
        before the requiring thing.

        The current implementation walks the resolved dependency graph, and
        make sure every node has a greater "weight" than all its parents.
        """
        assert self._result is not None
        weights = {None: 0}  # type: Dict[Optional[str], int]

        graph = self._result.graph
        while len(weights) < len(self._result.mapping):
            progressed = False
            for key in graph:
                if key in weights:
                    continue
                if not all(p in weights for p in graph.iter_parents(key)):
                    continue
                weight = max(weights[p] for p in graph.iter_parents(key)) + 1
                weights[key] = weight
                progressed = True

            # FIXME: This check will fail if there are unbreakable cycles.
            # Implement something to forcifully break them up to continue.
            assert progressed, "Order calculation stuck in dependency loop."

        sorted_items = sorted(
            req_set.requirements.items(),
            key=lambda item: weights[item[0]],
            reverse=True,
        )
        return [ireq for _, ireq in sorted_items]
