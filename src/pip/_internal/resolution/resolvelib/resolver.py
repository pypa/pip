import functools
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, cast

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible
from pip._vendor.resolvelib import Resolver as RLResolver
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.cache import WheelCache
from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.utils.direct_url_helpers import direct_url_from_link

from .base import Candidate, Requirement
from .factory import Factory
from .provider import PipProvider
from .reporter import PipDebuggingReporter, PipReporter

if TYPE_CHECKING:
    from pip._vendor.resolvelib.resolvers import Result as RLResult

    Result = RLResult[Requirement, Candidate, str]


logger = logging.getLogger(__name__)


class Resolver(BaseResolver):
    _allowed_strategies = {"eager", "only-if-needed", "to-satisfy-only"}

    def __init__(
        self,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        wheel_cache: Optional[WheelCache],
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        suppress_build_failures: bool,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ):
        super().__init__()
        assert upgrade_strategy in self._allowed_strategies

        self.factory = Factory(
            finder=finder,
            preparer=preparer,
            make_install_req=make_install_req,
            wheel_cache=wheel_cache,
            use_user_site=use_user_site,
            force_reinstall=force_reinstall,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            suppress_build_failures=suppress_build_failures,
            py_version_info=py_version_info,
        )
        self.ignore_dependencies = ignore_dependencies
        self.upgrade_strategy = upgrade_strategy
        self._result: Optional[Result] = None

    def _get_ireq(
        self,
        candidate: Candidate,
        direct_url_requested: bool,
    ) -> Optional[InstallRequirement]:
        """Get the InstallRequirement to install for a candidate.

        Returning None means the candidate is already satisfied by the current
        environment state and does not need to be handled.
        """
        ireq = candidate.get_install_requirement()

        # No ireq to install (e.g. extra-ed candidate). Skip.
        if ireq is None:
            return None

        # The currently installed distribution of the same identifier.
        installed_dist = self.factory.get_dist_to_uninstall(candidate)

        if installed_dist is None:  # Not installed. Install incoming candidate.
            return ireq

        # If we return this ireq, it should trigger uninstallation of the
        # existing distribution for reinstallation.
        ireq.should_reinstall = True

        # Reinstall if --force-reinstall is set.
        if self.factory.force_reinstall:
            return ireq

        # The artifact represented by the incoming candidate.
        cand_link = candidate.source_link

        # The candidate does not point to an artifact. This means the resolver
        # has already decided the installed distribution is good enough.
        if cand_link is None:
            return None

        # The incoming candidate was produced only from version requirements.
        # Reinstall if the installed distribution's version does not match.
        if not direct_url_requested:
            if installed_dist.version == candidate.version:
                return None
            return ireq

        # At this point, the incoming candidate was produced from a direct URL.
        # Determine whether to upgrade based on flags and whether the installed
        # distribution was done via a direct URL.

        # Always reinstall a direct candidate if it's on the local file system.
        if cand_link.is_file:
            return ireq

        # Reinstall if --upgrade is specified.
        if self.upgrade_strategy != "to-satisfy-only":
            return ireq

        # The PEP 610 direct URL representation of the installed distribution.
        dist_direct_url = installed_dist.direct_url

        # The incoming candidate was produced from a direct URL, but the
        # currently installed distribution was not. Always reinstall to be sure.
        if dist_direct_url is None:
            return ireq

        # Editable candidate always triggers reinstallation.
        if candidate.is_editable:
            return ireq

        # The currently installed distribution is editable, but the incoming
        # candidate is not. Uninstall the editable one to match.
        if installed_dist.editable:
            return ireq

        # Now we know both the installed distribution and incoming candidate
        # are based on direct URLs, and neither are editable. Don't reinstall
        # if the direct URLs match. Note that there's a special case for VCS: a
        # "unresolved" reference (e.g. branch) needs to be fully resolved for
        # comparison, so an updated remote branch can trigger reinstallation.
        # This is handled by the 'equivalent' implementation.
        cand_direct_url = direct_url_from_link(
            cand_link,
            ireq.source_dir,
            ireq.original_link_is_in_wheel_cache,
        )
        if cand_direct_url.equivalent(dist_direct_url):
            return None

        return ireq

    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        collected = self.factory.collect_root_requirements(root_reqs)
        provider = PipProvider(
            factory=self.factory,
            constraints=collected.constraints,
            ignore_dependencies=self.ignore_dependencies,
            upgrade_strategy=self.upgrade_strategy,
            user_requested=collected.user_requested,
        )
        if "PIP_RESOLVER_DEBUG" in os.environ:
            reporter: BaseReporter = PipDebuggingReporter()
        else:
            reporter = PipReporter()
        resolver: RLResolver[Requirement, Candidate, str] = RLResolver(
            provider,
            reporter,
        )

        try:
            try_to_avoid_resolution_too_deep = 2000000
            result = self._result = resolver.resolve(
                collected.requirements, max_rounds=try_to_avoid_resolution_too_deep
            )

        except ResolutionImpossible as e:
            error = self.factory.get_installation_error(
                cast("ResolutionImpossible[Requirement, Candidate]", e),
                collected.constraints,
            )
            raise error from e

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for identifier, candidate in result.mapping.items():
            # Whether the candidate was resolved from direct URL requirements.
            direct_url_requested = any(
                requirement.get_candidate_lookup()[0] is not None
                for requirement in result.criteria[identifier].iter_requirement()
            )

            ireq = self._get_ireq(candidate, direct_url_requested)
            if ireq is None:
                continue

            link = candidate.source_link
            if link and link.is_yanked:
                reason = link.yanked_reason or "<none given>"
                logger.warning(
                    "The candidate selected for download or install is a "
                    "yanked version: %r candidate (version %s at %s)\n"
                    "Reason for being yanked: %s",
                    candidate.name,
                    candidate.version,
                    link,
                    reason,
                )

            req_set.add_named_requirement(ireq)

        reqs = req_set.all_requirements
        self.factory.preparer.prepare_linked_requirements_more(reqs)
        return req_set

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        """Get order for installation of requirements in RequirementSet.

        The returned list contains a requirement before another that depends on
        it. This helps ensure that the environment is kept consistent as they
        get installed one-by-one.

        The current implementation creates a topological ordering of the
        dependency graph, giving more weight to packages with less
        or no dependencies, while breaking any cycles in the graph at
        arbitrary points. We make no guarantees about where the cycle
        would be broken, other than it *would* be broken.
        """
        assert self._result is not None, "must call resolve() first"

        if not req_set.requirements:
            # Nothing is left to install, so we do not need an order.
            return []

        graph = self._result.graph
        weights = get_topological_weights(graph, set(req_set.requirements.keys()))

        sorted_items = sorted(
            req_set.requirements.items(),
            key=functools.partial(_req_set_item_sorter, weights=weights),
            reverse=True,
        )
        return [ireq for _, ireq in sorted_items]


def get_topological_weights(
    graph: "DirectedGraph[Optional[str]]", requirement_keys: Set[str]
) -> Dict[Optional[str], int]:
    """Assign weights to each node based on how "deep" they are.

    This implementation may change at any point in the future without prior
    notice.

    We first simplify the dependency graph by pruning any leaves and giving them
    the highest weight: a package without any dependencies should be installed
    first. This is done again and again in the same way, giving ever less weight
    to the newly found leaves. The loop stops when no leaves are left: all
    remaining packages have at least one dependency left in the graph.

    Then we continue with the remaining graph, by taking the length for the
    longest path to any node from root, ignoring any paths that contain a single
    node twice (i.e. cycles). This is done through a depth-first search through
    the graph, while keeping track of the path to the node.

    Cycles in the graph result would result in node being revisited while also
    being on its own path. In this case, take no action. This helps ensure we
    don't get stuck in a cycle.

    When assigning weight, the longer path (i.e. larger length) is preferred.

    We are only interested in the weights of packages that are in the
    requirement_keys.
    """
    path: Set[Optional[str]] = set()
    weights: Dict[Optional[str], int] = {}

    def visit(node: Optional[str]) -> None:
        if node in path:
            # We hit a cycle, so we'll break it here.
            return

        # Time to visit the children!
        path.add(node)
        for child in graph.iter_children(node):
            visit(child)
        path.remove(node)

        if node not in requirement_keys:
            return

        last_known_parent_count = weights.get(node, 0)
        weights[node] = max(last_known_parent_count, len(path))

    # Simplify the graph, pruning leaves that have no dependencies.
    # This is needed for large graphs (say over 200 packages) because the
    # `visit` function is exponentially slower then, taking minutes.
    # See https://github.com/pypa/pip/issues/10557
    # We will loop until we explicitly break the loop.
    while True:
        leaves = set()
        for key in graph:
            if key is None:
                continue
            for _child in graph.iter_children(key):
                # This means we have at least one child
                break
            else:
                # No child.
                leaves.add(key)
        if not leaves:
            # We are done simplifying.
            break
        # Calculate the weight for the leaves.
        weight = len(graph) - 1
        for leaf in leaves:
            if leaf not in requirement_keys:
                continue
            weights[leaf] = weight
        # Remove the leaves from the graph, making it simpler.
        for leaf in leaves:
            graph.remove(leaf)

    # Visit the remaining graph.
    # `None` is guaranteed to be the root node by resolvelib.
    visit(None)

    # Sanity check: all requirement keys should be in the weights,
    # and no other keys should be in the weights.
    difference = set(weights.keys()).difference(requirement_keys)
    assert not difference, difference

    return weights


def _req_set_item_sorter(
    item: Tuple[str, InstallRequirement],
    weights: Dict[Optional[str], int],
) -> Tuple[int, str]:
    """Key function used to sort install requirements for installation.

    Based on the "weight" mapping calculated in ``get_installation_order()``.
    The canonical package name is returned as the second member as a tie-
    breaker to ensure the result is predictable, which is useful in tests.
    """
    name = canonicalize_name(item[0])
    return weights[name], name
