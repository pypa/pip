import mock
import pytest
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib.resolvers import Result
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.resolvelib.resolver import Resolver


@pytest.fixture()
def resolver(preparer, finder):
    resolver = Resolver(
        preparer=preparer,
        finder=finder,
        make_install_req=mock.Mock(),
        use_user_site="not-used",
        ignore_dependencies="not-used",
        ignore_installed="not-used",
        ignore_requires_python="not-used",
        force_reinstall="not-used",
        upgrade_strategy="not-used",
    )
    return resolver


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
                (None, "toporequire2"),
                (None, "toporequire3"),
                (None, "toporequire4"),
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
def test_rlr_resolver_get_installation_order(resolver, edges, ordered_reqs):
    # Build graph from edge declarations.
    graph = DirectedGraph()
    for parent, child in edges:
        parent = canonicalize_name(parent) if parent else None
        child = canonicalize_name(child) if child else None
        for v in (parent, child):
            if v not in graph:
                graph.add(v)
        graph.connect(parent, child)

    # Mapping values and criteria are not used in test, so we stub them out.
    mapping = {vertex: None for vertex in graph if vertex is not None}
    resolver._result = Result(mapping, graph, criteria=None)

    reqset = RequirementSet()
    for r in ordered_reqs:
        reqset.add_named_requirement(install_req_from_line(r))

    ireqs = resolver.get_installation_order(reqset)
    req_strs = [str(r.req) for r in ireqs]
    assert req_strs == ordered_reqs
