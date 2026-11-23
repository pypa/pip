# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import annotations

__lazy_modules__ = {
    "collections.abc",
    f"{__spec__.parent}.errors",
    f"{__spec__.parent}.requirements",
}

import re
from collections.abc import Mapping, Sequence

from .errors import _ErrorCollector
from .requirements import InvalidRequirement, Requirement

__all__ = [
    "CyclicDependencyGroup",
    "DependencyGroupInclude",
    "DependencyGroupResolver",
    "DuplicateGroupNames",
    "InvalidDependencyGroupObject",
    "resolve_dependency_groups",
]


def __dir__() -> list[str]:
    return __all__


# -----------
# Error Types
# -----------


class DuplicateGroupNames(ValueError):
    """
    The same dependency groups were defined twice, with different non-normalized names.

    .. versionadded:: 26.1
    """


class CyclicDependencyGroup(ValueError):
    """
    The dependency group includes form a cycle.

    .. versionadded:: 26.1
    """

    def __init__(self, requested_group: str, group: str, include_group: str) -> None:
        self.requested_group = requested_group
        self.group = group
        self.include_group = include_group

        if include_group == group:
            reason = f"{group} includes itself"
        else:
            reason = f"{include_group} -> {group}, {group} -> {include_group}"
        super().__init__(
            "Cyclic dependency group include while resolving "
            f"{requested_group}: {reason}"
        )

    # Support pickling; ``args`` does not match ``__init__``'s signature.
    def __reduce__(self) -> tuple[type[CyclicDependencyGroup], tuple[str, str, str]]:
        return (self.__class__, (self.requested_group, self.group, self.include_group))


# in the PEP 735 spec, the tables in dependency group lists were described as
# "Dependency Object Specifiers", but the only defined type of object was a
# "Dependency Group Include" -- hence the naming of this error as "Object"
class InvalidDependencyGroupObject(ValueError):
    """
    A member of a dependency group was identified as a dict, but was not in a valid
    format.

    .. versionadded:: 26.1
    """


# ------------------------
# Object Model & Interface
# ------------------------


class DependencyGroupInclude:
    """
    A reference to another dependency group by name.

    .. versionadded:: 26.1
    """

    __slots__ = ("include_group",)

    def __init__(self, include_group: str) -> None:
        """
        Initialize a DependencyGroupInclude.

        :param include_group: The name of the group referred to by this include.
        """
        self.include_group = include_group

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.include_group!r})"


class DependencyGroupResolver:
    """
    A resolver for Dependency Group data.

    This class handles caching, name normalization, cycle detection, and other
    parsing requirements. There are only two public methods for exploring the data:
    ``lookup()`` and ``resolve()``.

    :param dependency_groups: A mapping, as provided via pyproject
        ``[dependency-groups]``.

    .. versionadded:: 26.1
    """

    def __init__(
        self,
        dependency_groups: Mapping[str, Sequence[str | Mapping[str, str]]],
    ) -> None:
        errors = _ErrorCollector()

        self.dependency_groups = _normalize_group_names(dependency_groups, errors)

        # a map of group names to parsed data
        self._parsed_groups: dict[
            str, tuple[Requirement | DependencyGroupInclude, ...]
        ] = {}
        # a cache of completed resolutions to Requirement lists
        self._resolve_cache: dict[str, tuple[Requirement, ...]] = {}

        errors.finalize("[dependency-groups] data was invalid")

    def lookup(self, group: str) -> tuple[Requirement | DependencyGroupInclude, ...]:
        """
        Lookup a group name, returning the parsed dependency data for that group.
        This will not resolve includes.

        :param group: the name of the group to lookup
        """
        group = _normalize_name(group)

        with _ErrorCollector().on_exit(
            f"[dependency-groups] data for {group!r} was malformed"
        ) as errors:
            return self._parse_group(group, errors)

    def resolve(self, group: str) -> tuple[Requirement, ...]:
        """
        Resolve a dependency group to a list of requirements.

        :param group: the name of the group to resolve
        """
        group = _normalize_name(group)

        if group not in self._resolve_cache:
            with _ErrorCollector().on_exit(
                f"[dependency-groups] data for {group!r} was malformed"
            ) as errors:
                self._validate(group, group, [], set(), errors)

        return self._resolve(group)

    def _validate(
        self,
        group: str,
        requested_group: str,
        stack: list[str],
        visited: set[str],
        errors: _ErrorCollector,
    ) -> None:
        """
        Parse every group reachable from ``group`` exactly once and record parse
        errors and include cycles in ``errors``.

        :param group: The normalized name of the group to validate.
        :param requested_group: The group which was used in the original, user-facing
            request.
        :param stack: The groups on the current include path.
        :param visited: The groups which were already validated in this call.
        :param errors: An error collector in active use.
        """
        visited.add(group)
        stack.append(group)
        for item in self._parse_group(group, errors):
            if isinstance(item, DependencyGroupInclude):
                include_group = _normalize_name(item.include_group)
                if include_group in stack:
                    errors.error(
                        CyclicDependencyGroup(requested_group, group, include_group)
                    )
                elif include_group not in visited:
                    self._validate(
                        include_group, requested_group, stack, visited, errors
                    )
        stack.pop()

    def _resolve(self, group: str) -> tuple[Requirement, ...]:
        """
        Resolve a group which ``_validate`` accepted, using the cache.

        :param group: The normalized name of the group to resolve.
        """
        if group not in self._resolve_cache:
            resolved: list[Requirement] = []
            for item in self._parsed_groups[group]:
                if isinstance(item, Requirement):
                    resolved.append(item)
                else:
                    resolved.extend(self._resolve(_normalize_name(item.include_group)))
            self._resolve_cache[group] = tuple(resolved)
        return self._resolve_cache[group]

    def _parse_group(
        self, group: str, errors: _ErrorCollector
    ) -> tuple[Requirement | DependencyGroupInclude, ...]:
        # short circuit -- never do the work twice
        if group in self._parsed_groups:
            return self._parsed_groups[group]

        if group not in self.dependency_groups:
            errors.error(LookupError(f"Dependency group '{group}' not found"))
            return ()

        raw_group = self.dependency_groups[group]
        if isinstance(raw_group, str):
            errors.error(
                TypeError(
                    f"Dependency group {group!r} contained a string rather than a list."
                )
            )
            return ()

        if not isinstance(raw_group, Sequence):
            errors.error(
                TypeError(f"Dependency group {group!r} is not a sequence type.")
            )
            return ()

        elements: list[Requirement | DependencyGroupInclude] = []
        error_count_before_parse = len(errors.errors)
        for item in raw_group:
            if isinstance(item, str):
                # packaging.requirements.Requirement parsing ensures that this is a
                # valid PEP 508 Dependency Specifier. Collect InvalidRequirement
                # if it throws that.
                with errors.collect(InvalidRequirement):
                    elements.append(Requirement(item))
            elif isinstance(item, Mapping):
                if tuple(item.keys()) != ("include-group",):
                    errors.error(
                        InvalidDependencyGroupObject(
                            f"Invalid dependency group item: {item!r}"
                        )
                    )
                else:
                    include_group = item["include-group"]
                    if not isinstance(include_group, str):
                        msg = (
                            "Dependency group include-group value is not a string: "
                            f"{item!r}"
                        )
                        errors.error(TypeError(msg))
                    else:
                        elements.append(
                            DependencyGroupInclude(include_group=include_group)
                        )
            else:
                errors.error(TypeError(f"Invalid dependency group item: {item!r}"))

        # Return valid includes for validation even if other items failed.
        # Cache only complete, successful parses.
        parsed = tuple(elements)
        if len(errors.errors) == error_count_before_parse:
            self._parsed_groups[group] = parsed
        return parsed


# --------------------
# Functional Interface
# --------------------


def resolve_dependency_groups(
    dependency_groups: Mapping[str, Sequence[str | Mapping[str, str]]], /, *groups: str
) -> tuple[str, ...]:
    """
    Resolve a dependency group to a tuple of requirements, as strings.

    :param dependency_groups: the parsed contents of the ``[dependency-groups]`` table
        from ``pyproject.toml``
    :param groups: the name of the group(s) to resolve

    .. versionadded:: 26.1
    """
    resolver = DependencyGroupResolver(dependency_groups)
    return tuple(str(r) for group in groups for r in resolver.resolve(group))


# ----------------
# internal helpers
# ----------------


_NORMALIZE_PATTERN = re.compile(r"[-_.]+")


def _normalize_name(name: str) -> str:
    return _NORMALIZE_PATTERN.sub("-", name).lower()


def _normalize_group_names(
    dependency_groups: Mapping[str, Sequence[str | Mapping[str, str]]],
    errors: _ErrorCollector,
) -> dict[str, Sequence[str | Mapping[str, str]]]:
    original_names: dict[str, list[str]] = {}
    normalized_groups: dict[str, Sequence[str | Mapping[str, str]]] = {}

    for group_name, value in dependency_groups.items():
        normed_group_name = _normalize_name(group_name)
        original_names.setdefault(normed_group_name, []).append(group_name)
        normalized_groups[normed_group_name] = value

    for normed_name, names in original_names.items():
        if len(names) > 1:
            errors.error(
                DuplicateGroupNames(
                    "Duplicate dependency group names: "
                    f"{normed_name} ({', '.join(names)})"
                )
            )

    return normalized_groups
