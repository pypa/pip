from unittest import mock

import pytest
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib.resolvers import Result
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.resolvelib.resolver import (
    Resolver,
    get_topological_weights,
)


@pytest.fixture()
def resolver(preparer, finder):
    resolver = Resolver(
        preparer=preparer,
        finder=finder,
        wheel_cache=None,
        make_install_req=mock.Mock(),
        use_user_site="not-used",
        ignore_dependencies="not-used",
        ignore_installed="not-used",
        ignore_requires_python="not-used",
        force_reinstall="not-used",
        upgrade_strategy="to-satisfy-only",
    )
    return resolver


def _make_graph(edges):
    """Build graph from edge declarations."""

    graph = DirectedGraph()
    for parent, child in edges:
        parent = canonicalize_name(parent) if parent else None
        child = canonicalize_name(child) if child else None
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
    ],
)
def test_new_resolver_get_installation_order(resolver, edges, ordered_reqs):
    graph = _make_graph(edges)

    # Mapping values and criteria are not used in test, so we stub them out.
    mapping = {vertex: None for vertex in graph if vertex is not None}
    resolver._result = Result(mapping, graph, criteria=None)

    reqset = RequirementSet()
    for r in ordered_reqs:
        reqset.add_named_requirement(install_req_from_line(r))

    ireqs = resolver.get_installation_order(reqset)
    req_strs = [str(r.req) for r in ireqs]
    assert req_strs == ordered_reqs


@pytest.mark.parametrize(
    "name, edges, expected_weights",
    [
        (
            # From https://github.com/pypa/pip/pull/8127#discussion_r414564664
            "deep second edge",
            [
                (None, "one"),
                (None, "two"),
                ("one", "five"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
            ],
            {None: 0, "one": 1, "two": 1, "three": 2, "four": 3, "five": 4},
        ),
        (
            "linear",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND root -> two",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                (None, "two"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND root -> three",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                (None, "three"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND root -> four",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                (None, "four"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND root -> five",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                (None, "five"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND one -> four",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                ("one", "four"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND two -> four",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                ("two", "four"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND four -> one (cycle)",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                ("four", "one"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND four -> two (cycle)",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                ("four", "two"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
        (
            "linear AND four -> three (cycle)",
            [
                (None, "one"),
                ("one", "two"),
                ("two", "three"),
                ("three", "four"),
                ("four", "five"),
                ("four", "three"),
            ],
            {None: 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5},
        ),
    ],
)
def test_new_resolver_topological_weights(name, edges, expected_weights):
    graph = _make_graph(edges)

    weights = get_topological_weights(graph, len(expected_weights))
    assert weights == expected_weights
