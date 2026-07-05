from __future__ import annotations

import functools
import logging
import os
from collections import deque
from typing import TYPE_CHECKING, cast

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible, ResolutionTooDeep
from pip._vendor.resolvelib import Resolver as RLResolver
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.cache import WheelCache
from pip._internal.exceptions import ResolutionTooDeepError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (
    PipDebuggingReporter,
    PipReporter,
)

from .base import Candidate, Requirement
from .candidates import as_base_candidate
from .factory import Factory

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
        wheel_cache: WheelCache | None,
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        py_version_info: tuple[int, ...] | None = None,
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
            py_version_info=py_version_info,
        )
        self.ignore_dependencies = ignore_dependencies
        self.upgrade_strategy = upgrade_strategy
        self._result: Result | None = None

    def resolve(
        self, root_reqs: list[InstallRequirement], check_supported_wheels: bool
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
            reporter: BaseReporter[Requirement, Candidate, str] = PipDebuggingReporter()
        else:
            reporter = PipReporter(constraints=provider.constraints)

        resolver: RLResolver[Requirement, Candidate, str] = RLResolver(
            provider,
            reporter,
        )

        try:
            limit_how_complex_resolution_can_be = 200000
            result = self._result = resolver.resolve(
                collected.requirements, max_rounds=limit_how_complex_resolution_can_be
            )

        except ResolutionImpossible as e:
            error = self.factory.get_installation_error(
                cast("ResolutionImpossible[Requirement, Candidate]", e),
                collected.constraints,
            )
            raise error from e
        except ResolutionTooDeep:
            raise ResolutionTooDeepError from None

        # Extras are an attribute of a single resolver node, so a project stays
        # pinned with an extra even after the requirement that asked for it is
        # backtracked away, leaving that extra's dependencies stranded in the
        # mapping. Re-derive which extras each project still needs, and skip the
        # stranded nodes, so the install set matches what the solution requires.
        required_extras = self._reachable_extras(result, collected.requirements)

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for name, pinned in result.mapping.items():
            extras = required_extras.get(name)
            if extras is None:
                # Held only by a stale extra that nothing still requests.
                continue

            if extras == pinned.extras:
                candidate: Candidate = pinned
            else:
                # The pin carries more extras than survived, so it is an
                # ExtrasCandidate; install its base under only the extras still
                # required.
                base = as_base_candidate(pinned.base_candidate)
                assert base is not None, "only an ExtrasCandidate can shed extras"
                candidate = (
                    self.factory.make_extras_candidate(base, extras) if extras else base
                )

            ireq = candidate.get_install_requirement()
            if ireq is None:
                continue

            # Check if there is already an installation under the same name,
            # and set a flag for later stages to uninstall it, if needed.
            installed_dist = self.factory.get_dist_to_uninstall(candidate)
            if installed_dist is None:
                # There is no existing installation -- nothing to uninstall.
                ireq.should_reinstall = False
            elif self.factory.force_reinstall:
                # The --force-reinstall flag is set -- reinstall.
                ireq.should_reinstall = True
            elif installed_dist.version != candidate.version:
                # The installation is different in version -- reinstall.
                ireq.should_reinstall = True
            elif candidate.is_editable or installed_dist.editable:
                # The incoming distribution is editable, or different in
                # editable-ness to installation -- reinstall.
                ireq.should_reinstall = True
            elif candidate.source_link and candidate.source_link.is_file:
                # The incoming distribution is under file://
                if candidate.source_link.is_wheel:
                    # is a local wheel -- do nothing.
                    logger.info(
                        "%s is already installed with the same version as the "
                        "provided wheel. Use --force-reinstall to force an "
                        "installation of the wheel.",
                        ireq.name,
                    )
                    continue

                # is a local sdist or path -- reinstall
                ireq.should_reinstall = True
            else:
                continue

            link = candidate.source_link
            if link and link.is_yanked:
                # The reason can contain non-ASCII characters, Unicode
                # is required for Python 2.
                msg = (
                    "The candidate selected for download or install is a "
                    "yanked version: {name!r} candidate (version {version} "
                    "at {link})\nReason for being yanked: {reason}"
                ).format(
                    name=candidate.name,
                    version=candidate.version,
                    link=link,
                    reason=link.yanked_reason or "<none given>",
                )
                logger.warning(msg)

            req_set.add_named_requirement(ireq)

        return req_set

    def _reachable_extras(
        self,
        result: Result,
        roots: list[Requirement],
    ) -> dict[str, frozenset[NormalizedName]]:
        """Map each installable project to the extras it still requires.

        A project stays pinned with an extra even after the requirement that
        asked for it is backtracked away (see the note in ``resolve``), which
        strands that extra's dependencies in ``result.mapping``. Walk the
        solution from the root requirements, re-deriving each project's
        dependencies under only the extras still asked of it; projects the walk
        never reaches were held solely by a stale extra and are dropped.
        """
        mapping = result.mapping

        # Without extras nothing is stranded and every pinned node is reachable.
        if not any(candidate.extras for candidate in mapping.values()):
            return {name: frozenset() for name in mapping}

        active: dict[str, set[NormalizedName]] = {}
        queue: deque[str] = deque()

        # Record the extras asked of a node, re-queueing it when they grow.
        def request(name: str, extras: frozenset[NormalizedName]) -> None:
            reached = active.get(name)
            if reached is None:
                active[name] = set(extras)
                queue.append(name)
            elif not extras <= reached:
                reached |= extras
                queue.append(name)

        for root in roots:
            if root.project_name in mapping:
                request(root.project_name, root.extras)

        while queue:
            name = queue.popleft()
            for child, child_extras in self._derived_edges(name, active[name]):
                request(child, child_extras)

        return {name: frozenset(extras) for name, extras in active.items()}

    def _derived_edges(
        self, name: str, extras: set[NormalizedName]
    ) -> list[tuple[str, frozenset[NormalizedName]]]:
        """A project's in-solution dependencies under ``extras``.

        Reads the edges from the resolved candidate, keeping only those whose
        target is in the solution. Extras the project does not provide are
        dropped: they pull nothing, and re-deriving them would repeat the "does
        not provide the extra" warning already emitted during resolve.
        """
        assert self._result is not None
        mapping = self._result.mapping

        base = as_base_candidate(mapping[name].base_candidate)
        if base is None:
            # The Requires-Python node has no dependencies to contribute.
            return []

        # Read the dependencies under only the extras the project provides.
        valid = frozenset(base.dist.iter_provided_extras()) & extras
        source = self.factory.make_extras_candidate(base, valid) if valid else base
        return [
            (dep.project_name, dep.extras)
            for dep in source.iter_dependencies(not self.ignore_dependencies)
            if dep is not None and dep.project_name in mapping
        ]

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> list[InstallRequirement]:
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
    graph: DirectedGraph[str | None], requirement_keys: set[str]
) -> dict[str | None, int]:
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
    path: set[str | None] = set()
    weights: dict[str | None, list[int]] = {}

    def visit(node: str | None) -> None:
        if node in path:
            # We hit a cycle, so we'll break it here.
            return

        # The walk is exponential and for pathologically connected graphs (which
        # are the ones most likely to contain cycles in the first place) it can
        # take until the heat-death of the universe. To counter this we limit
        # the number of attempts to visit (i.e. traverse through) any given
        # node. We choose a value here which gives decent enough coverage for
        # fairly well behaved graphs, and still limits the walk complexity to be
        # linear in nature.
        cur_weights = weights.get(node, [])
        if len(cur_weights) >= 5:
            return

        # Time to visit the children!
        path.add(node)
        for child in graph.iter_children(node):
            visit(child)
        path.remove(node)

        if node not in requirement_keys:
            return

        cur_weights.append(len(path))
        weights[node] = cur_weights

    # Simplify the graph, pruning leaves that have no dependencies. This is
    # needed for large graphs (say over 200 packages) because the `visit`
    # function is slower for large/densely connected graphs, taking minutes.
    # See https://github.com/pypa/pip/issues/10557
    # We repeat the pruning step until we have no more leaves to remove.
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
            weights[leaf] = [weight]
        # Remove the leaves from the graph, making it simpler.
        for leaf in leaves:
            graph.remove(leaf)

    # Visit the remaining graph, this will only have nodes to handle if the
    # graph had a cycle in it, which the pruning step above could not handle.
    # `None` is guaranteed to be the root node by resolvelib.
    visit(None)

    # Sanity check: all requirement keys should be in the weights,
    # and no other keys should be in the weights.
    difference = set(weights.keys()).difference(requirement_keys)
    assert not difference, difference

    # Now give back all the weights, choosing the largest ones from what we
    # accumulated.
    return {node: max(wgts) for (node, wgts) in weights.items()}


def _req_set_item_sorter(
    item: tuple[str, InstallRequirement],
    weights: dict[str | None, int],
) -> tuple[int, str]:
    """Key function used to sort install requirements for installation.

    Based on the "weight" mapping calculated in ``get_installation_order()``.
    The canonical package name is returned as the second member as a tie-
    breaker to ensure the result is predictable, which is useful in tests.
    """
    name = canonicalize_name(item[0])
    return weights[name], name
