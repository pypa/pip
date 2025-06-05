from __future__ import annotations

from typing import cast
from unittest import mock

import pytest

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib.resolvers import Result
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.resolvelib.resolver import Resolver


@pytest.fixture
def resolver(preparer: RequirementPreparer, finder: PackageFinder) -> Resolver:
    resolver = Resolver(
        preparer=preparer,
        finder=finder,
        wheel_cache=None,
        make_install_req=mock.Mock(),
        use_user_site=False,
        ignore_dependencies=False,
        ignore_installed=False,
        ignore_requires_python=False,
        force_reinstall=False,
        upgrade_strategy="to-satisfy-only",
    )
    return resolver


def _make_graph(
    edges: list[tuple[str | None, str | None]],
) -> DirectedGraph[str | None]:
    """Build graph from edge declarations."""

    graph: DirectedGraph[str | None] = DirectedGraph()
    for parent, child in edges:
        parent = cast(str, canonicalize_name(parent)) if parent else None
        child = cast(str, canonicalize_name(child)) if child else None
        for v in (parent, child):
            if v not in graph:
                graph.add(v)
        graph.connect(parent, child)
    return graph


@pytest.mark.parametrize(
    "edges, ordered_reqs",
    [
        (
            [(None, "require-simple"), ("require-simple", "simple")],
            ["simple==3.0", "require-simple==1.0"],
        ),
        (
            [(None, "meta"), ("meta", "simple"), ("meta", "simple2")],
            ["simple2==3.0", "simple==3.0", "meta==1.0"],
        ),
        (
            [
                (None, "toporequires"),
                (None, "toporequires2"),
                (None, "toporequires3"),
                (None, "toporequires4"),
                ("toporequires2", "toporequires"),
                ("toporequires3", "toporequires"),
                ("toporequires4", "toporequires"),
                ("toporequires4", "toporequires2"),
                ("toporequires4", "toporequires3"),
            ],
            [
                "toporequires==0.0.1",
                "toporequires3==0.0.1",
                "toporequires2==0.0.1",
                "toporequires4==0.0.1",
            ],
        ),
        (
            [
                (None, "left"),
                (None, "right"),
                ("left", "left-left"),
                ("left", "left-right"),
                ("left-left", "left-left-left"),
                ("right", "right-left"),
            ],
            [
                "right-left==0.0.1",
                "left-right==0.0.1",
                "left-left-left==0.0.1",
                "right==0.0.1",
                "left-left==0.0.1",
                "left==0.0.1",
            ],
        ),
    ],
)
def test_new_resolver_get_installation_order(
    resolver: Resolver,
    edges: list[tuple[str | None, str | None]],
    ordered_reqs: list[str],
) -> None:
    graph = _make_graph(edges)

    # Mapping values and criteria are not used in test, so we stub them out.
    mapping = {vertex: None for vertex in graph if vertex is not None}
    resolver._result = Result(mapping, graph, criteria=None)  # type: ignore

    reqset = RequirementSet()
    for r in ordered_reqs:
        reqset.add_named_requirement(install_req_from_line(r))

    ireqs = resolver.get_installation_order(reqset)
    req_strs = [str(r.req) for r in ireqs]
    assert req_strs == ordered_reqs
