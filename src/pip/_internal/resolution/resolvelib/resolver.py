import functools
import logging

from pip._vendor import six
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible
from pip._vendor.resolvelib import Resolver as RLResolver

from pip._internal.exceptions import InstallationError
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .factory import Factory

if MYPY_CHECK_RUNNING:
    from typing import Dict, List, Optional, Tuple

    from pip._vendor.resolvelib.resolvers import Result
    from pip._vendor.resolvelib.structs import Graph

    from pip._internal.cache import WheelCache
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.resolution.base import InstallRequirementProvider


logger = logging.getLogger(__name__)


class Resolver(BaseResolver):
    def __init__(
        self,
        preparer,  # type: RequirementPreparer
        finder,  # type: PackageFinder
        wheel_cache,  # type: Optional[WheelCache]
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
        self.factory = Factory(
            finder=finder,
            preparer=preparer,
            make_install_req=make_install_req,
            force_reinstall=force_reinstall,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            py_version_info=py_version_info,
        )
        self.ignore_dependencies = ignore_dependencies
        self._result = None  # type: Optional[Result]

    def resolve(self, root_reqs, check_supported_wheels):
        # type: (List[InstallRequirement], bool) -> RequirementSet

        # FIXME: Implement constraints.
        if any(r.constraint for r in root_reqs):
            raise InstallationError("Constraints are not yet supported.")

        provider = PipProvider(
            factory=self.factory,
            ignore_dependencies=self.ignore_dependencies,
        )
        reporter = BaseReporter()
        resolver = RLResolver(provider, reporter)

        requirements = [
            self.factory.make_requirement_from_install_req(r)
            for r in root_reqs
        ]

        try:
            self._result = resolver.resolve(requirements)

        except ResolutionImpossible as e:
            error = self.factory.get_installation_error(e)
            if not error:
                # TODO: This needs fixing, we need to look at the
                # factory.get_installation_error infrastructure, as that
                # doesn't really allow for the logger.critical calls I'm
                # using here.
                for req, parent in e.causes:
                    logger.critical(
                        "Could not find a version that satisfies " +
                        "the requirement " +
                        str(req) +
                        ("" if parent is None else " (from {})".format(
                            parent.name
                        ))
                    )
                raise InstallationError(
                    "No matching distribution found for " +
                    ", ".join([r.name for r, _ in e.causes])
                )
                raise
            six.raise_from(error, e)

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for candidate in self._result.mapping.values():
            ireq = provider.get_install_requirement(candidate)
            if ireq is None:
                continue
            ireq.should_reinstall = self.factory.should_reinstall(candidate)
            req_set.add_named_requirement(ireq)

        return req_set

    def get_installation_order(self, req_set):
        # type: (RequirementSet) -> List[InstallRequirement]
        """Get order for installation of requirements in RequirementSet.

        The returned list contains a requirement before another that depends on
        it. This helps ensure that the environment is kept consistent as they
        get installed one-by-one.

        The current implementation walks the resolved dependency graph, and
        make sure every node has a greater "weight" than all its parents.
        """
        assert self._result is not None, "must call resolve() first"

        graph = self._result.graph
        weights = get_topological_weights(graph)

        sorted_items = sorted(
            req_set.requirements.items(),
            key=functools.partial(_req_set_item_sorter, weights=weights),
            reverse=True,
        )
        return [ireq for _, ireq in sorted_items]


def get_topological_weights(graph):
    # type: (Graph) -> Dict[str, int]
    """Assign weights to each node based on how "deep" they are.
    """
    visited = set()  # type: Set[str]
    weights = {}

    key_count = len(graph)
    while len(weights) < key_count:
        progressed = False
        for key in graph:
            if key in weights:
                continue
            parents = list(graph.iter_parents(key))
            if not all(p in weights for p in parents):
                continue
            if parents:
                weight = max(weights[p] for p in parents) + 1
            else:
                weight = 0
            weights[key] = weight
            progressed = True

        # FIXME: This check will fail if there are unbreakable cycles.
        # Implement something to forcifully break them up to continue.
        if not progressed:
            raise InstallationError(
                "Could not determine installation order due to cicular "
                "dependency."
            )

    return weights


def _req_set_item_sorter(
    item,     # type: Tuple[str, InstallRequirement]
    weights,  # type: Dict[Optional[str], int]
):
    # type: (...) -> Tuple[int, str]
    """Key function used to sort install requirements for installation.

    Based on the "weight" mapping calculated in ``get_installation_order()``.
    The canonical package name is returned as the second member as a tie-
    breaker to ensure the result is predictable, which is useful in tests.
    """
    name = canonicalize_name(item[0])
    return weights[name], name
