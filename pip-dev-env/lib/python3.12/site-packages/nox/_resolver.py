# Copyright 2022 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import itertools
from collections import OrderedDict
from typing import Hashable, Iterable, Iterator, Mapping, TypeVar

__all__ = ["CycleError", "lazy_stable_topo_sort"]


def __dir__() -> list[str]:
    return __all__


Node = TypeVar("Node", bound=Hashable)


class CycleError(ValueError):
    """An exception indicating that a cycle was encountered in a graph."""


def lazy_stable_topo_sort(
    dependencies: Mapping[Node, Iterable[Node]],
    root: Node,
    *,
    drop_root: bool = True,
) -> Iterator[Node]:
    """Returns the "lazy, stable" topological sort of a dependency graph.

    The sort returned will be a topological sort of the subgraph containing only
    ``root`` and its (recursive) dependencies. ``root`` will not be included in the
    output sort if ``drop_root`` is ``True``.

    The sort returned is "lazy" in the sense that a node will not appear any earlier in
    the output sort than is necessitated by its dependents.

    The sort returned is "stable" in the sense that the relative order of two nodes in
    ``dependencies[node]`` is preserved in the output sort, except when doing so would
    prevent the output sort from being either topological or lazy. The order of nodes in
    ``dependencies[node]`` allows the caller to exert a preference on the order of the
    output sort.

    For example, consider:

    >>> list(
    ...     lazy_stable_topo_sort(
    ...         dependencies = {
    ...             "a": ["c", "b"],
    ...             "b": [],
    ...             "c": [],
    ...             "d": ["e"],
    ...             "e": ["c"],
    ...             "root": ["a", "d"],
    ...         },
    ...         "root",
    ...         drop_root=False,
    ...     )
    ... )
    ["c", "b", "a", "e", "d", "root"]

    Notice that:

        1.  This is a topological sort of the dependency graph. That is, nodes only
            occur in the sort after all of their dependencies occur.

        2.  Had we also included a node ``"f": ["b"]`` but kept ``dependencies["root"]``
            the same, the output would not have changed. This is because ``"f"`` was not
            requested directly by including it in ``dependencies["root"]`` or
            transitively as a (recursive) dependency of a node in
            ``dependencies["root"]``.

        3.  ``"e"`` occurs no earlier than was required by its dependents ``{"d"}``.
            This is an example of the sort being "lazy". If ``"e"`` had occurred in the
            output any earlier---for example, just before ``"a"``---the sort would not
            have been lazy, but (in this example) the output would still have been a
            topological sort.

        4.  Because the topological order between ``"a"`` and ``"d"`` is undefined and
            because it is possible to do so without making the output sort non-lazy,
            ``"a"`` and ``"d"`` are kept in the relative order that they have in
            ``dependencies["root"]``. This is an example of the sort being stable
            between pairs in ``dependencies[node]`` whenever possible. If ``"a"``'s
            dependency list was instead ``["d"]``, however, the relative order between
            ``"a"`` and ``"d"`` in ``dependencies["root"]`` would have been ignored to
            satisfy this dependency.

            Similarly, ``"b"`` and ``"c"`` are kept in the relative order that they have
            in ``dependencies["a"]``. If ``"c"``'s dependency list was instead
            ``["b"]``, however, the relative order between ``"b"`` and ``"c"`` in
            ``dependencies["a"]`` would have been ignored to satisfy this dependency.

    This implementation of this function is recursive and thus should not be used on
    large dependency graphs, but it is suitable for noxfile-sized dependency graphs.

    Args:
        dependencies (Mapping[~nox._resolver.Node, Iterable[~nox._resolver.Node]]):
            A mapping from each node in the graph to the (ordered) list of nodes that it
            depends on. Using a mapping type with O(1) lookup (e.g. `dict`) is strongly
            suggested.
        root (~nox._resolver.Node):
            The root node to start the sort at. If ``drop_root`` is not ``True``,
            ``root`` will be the last element of the output.
        drop_root (bool):
            If ``True``, ``root`` will be not be included in the output sort. Defaults
            to ``True``.


    Returns:
        Iterator[~nox._resolver.Node]: The "lazy, stable" topological sort of the
        subgraph containing ``root`` and its dependencies.

    Raises:
        ~nox._resolver.CycleError: If a dependency cycle is encountered.
    """

    visited = dict.fromkeys(dependencies, False)

    def prepended_by_dependencies(
        node: Node,
        walk: OrderedDict[Node, None] | None = None,
    ) -> Iterator[Node]:
        """Yields a node's dependencies depth-first, followed by the node itself.

        A dependency will be skipped if has already been yielded by another call of
        ``prepended_by_dependencies``. Since ``prepended_by_dependencies`` is recursive,
        this means that each node will only be yielded once, and only the deepest
        occurrence of a node will be yielded.

        Args:
            node (~nox._resolver.Node):
                A node in the dependency graph.
            walk (OrderedDict[~nox._resolver.Node, None] | None):
                An ``OrderedDict`` whose keys are the nodes traversed when walking a
                path leading up to ``node`` on the reversed-edge dependency graph.
                Defaults to ``OrderedDict()``.

        Yields:
            ~nox._resolver.Node: ``node``'s direct dependencies, each
            prepended by their own direct dependencies, and so forth recursively,
            depth-first, followed by ``node``.

        Raises:
            ValueError: If a dependency cycle is encountered.
        """
        nonlocal visited
        # We would like for ``walk`` to be an ordered set so that we get (a) O(1) ``node
        # in walk`` and (b) so that we can use the order to report to the user what the
        # dependency cycle is, if one is encountered. The standard library does not have
        # an ordered set type, so we instead use the keys of an ``OrderedDict[Node,
        # None]`` as an ordered set.
        walk = walk or OrderedDict()
        walk = extend_walk(walk, node)
        if not visited[node]:
            visited[node] = True
            # Recurse for each node in dependencies[node] in order so that we adhere to
            # the ``dependencies[node]`` order preference if doing so is possible.
            yield from itertools.chain.from_iterable(
                prepended_by_dependencies(dependency, walk)
                for dependency in dependencies[node]
            )
            yield node
        else:
            return

    def extend_walk(
        walk: OrderedDict[Node, None], node: Node
    ) -> OrderedDict[Node, None]:
        """Extend a walk by a node, checking for dependency cycles.

        Args:
            walk (OrderedDict[~nox._resolver.Node, None]):
                See ``prepended_by_dependencies``.
            nodes (~nox._resolver.Node):
                A node to extend the walk with.

        Returns:
            OrderedDict[~nox._resolver.Node, None]: ``walk``, extended by
            ``node``.

        Raises:
            ValueError: If extending ``walk`` by ``node`` introduces a cycle into the
                represented walk on the dependency graph.
        """
        walk = walk.copy()
        if node in walk:
            # Dependency cycle found.
            walk_list = list(walk)
            cycle = walk_list[walk_list.index(node) :] + [node]
            msg = "Nodes are in a dependency cycle"
            raise CycleError(msg, tuple(cycle))
        walk[node] = None
        return walk

    sort = prepended_by_dependencies(root)
    if drop_root:
        return filter(
            lambda node: not (node == root and hash(node) == hash(root)), sort
        )
    return sort
