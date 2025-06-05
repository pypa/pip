from __future__ import annotations

import contextlib
import logging
import os
import sys
from typing import TYPE_CHECKING, Tuple, cast

from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible, ResolutionTooDeep
from pip._vendor.resolvelib import Resolver as RLResolver

from pip._internal.cache import WheelCache
from pip._internal.exceptions import ResolutionTooDeepError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_extend_extras
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (
    PipDebuggingReporter,
    PipReporter,
)
from pip._internal.utils.packaging import get_requirement

from .base import Candidate, Requirement
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
            reporter = PipReporter()
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

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        # process candidates with extras last to ensure their base equivalent is
        # already in the req_set if appropriate.
        # Python's sort is stable so using a binary key function keeps relative order
        # within both subsets.
        for candidate in sorted(
            result.mapping.values(), key=lambda c: c.name != c.project_name
        ):
            ireq = candidate.get_install_requirement()
            if ireq is None:
                if candidate.name != candidate.project_name:
                    # extend existing req's extras
                    with contextlib.suppress(KeyError):
                        req = req_set.get_requirement(candidate.project_name)
                        req_set.add_named_requirement(
                            install_req_extend_extras(
                                req, get_requirement(candidate.name).extras
                            )
                        )
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

        reqs = req_set.all_requirements
        self.factory.preparer.prepare_linked_requirements_more(reqs)
        for req in reqs:
            req.prepared = True
            req.needs_more_preparation = False
        return req_set

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> list[InstallRequirement]:
        """Get order for installation of requirements in RequirementSet.

        The returned list contains a requirement before another that depends on
        it. This helps ensure that the environment is kept consistent as they
        get installed one-by-one.

        The current implementation creates a topological ordering of the
        dependency graph, while breaking any cycles in the graph at
        arbitrary points. We make no guarantees about where the cycle
        would be broken, other than it *would* be broken.
        """

        def has_children(node: str | None) -> bool:
            for _ in graph.iter_children(node):
                return True
            return False

        assert self._result is not None, "must call resolve() first"

        if not req_set.requirements:
            # Nothing is left to install, so we do not need an order.
            return []

        # Copy the graph since we are going to mutate it.
        graph = self._result.graph.copy()

        # Remove anything from the graph which is not required. This simplifies
        # the graph so we don't consider any nodes which we don't need to.
        for node in set(graph).difference(req_set.requirements.keys()):
            graph.remove(node)

        # We will create an ordered list of names, with the ones which we want
        # to install first at the front. We do this by repeatedly attempting to
        # prune leaves from the graph until it's empty. Leaves are nodes which
        # don't depend on any other nodes in the graph (i.e. have no children).
        names = []
        pruning = True
        while len(graph) > 0:
            # Remove all the leaves we can at the graph extremities, working our
            # way inwards with each iteration. We try again and again, since
            # each round of pruning may create more leaves. We walk the names in
            # reverse asciibetical order so that the ordering is stable between
            # runs and conforms to historical behavior.
            while pruning:
                # Determine the leaves as a first step, and remove them as a
                # second step. We do it in two stages way since it's more
                # breadth-first than depth-first, so preserves overall
                # leaf-to-root distance semantics across all the leaves.
                pruning = False
                named_nodes = [n for n in graph if n is not None]
                for node in [
                    n for n in sorted(named_nodes, reverse=True) if not has_children(n)
                ]:
                    pruning = True
                    names.append(node)
                    graph.remove(node)

            # If we pruned the leaves from the graph, but there are still nodes
            # in it, then this implies that there is a cycle. We look for the
            # node which is the most "leaf-like" (fewest children) and a high
            # chance of being in the cycle (most parents). We remove that node
            # in an attempt to break the cycle. This isn't guaranteed to work
            # but such a node is something which we'll likely want to install in
            # preference to other nodes anyhow. Since we'll keep doing this we
            # are going to break the cycle _eventually_.
            if len(graph) > 0:
                target: Tuple[str | None, int, int] = (None, -1, sys.maxsize)
                named_nodes = [n for n in graph if n is not None]
                for node in sorted(named_nodes, reverse=True):
                    num_parents = len(tuple(graph.iter_parents(node)))
                    num_children = len(tuple(graph.iter_children(node)))
                    if num_parents > target[1] and num_children < target[2]:
                        target = (node, num_parents, num_children)
                if target[0] is not None:
                    names.append(target[0])
                graph.remove(target[0])

                # We attempted to break the cycle so we're still trying to
                # prune.
                pruning = True

        # When we get here the graph has been completely emptied and the ordered
        # list of names can be mapped back to the requirements.
        difference = set(names).difference(req_set.requirements.keys())
        assert not difference, difference
        return [req_set.get_requirement(name) for name in names]
