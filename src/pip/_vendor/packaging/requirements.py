# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import annotations

__lazy_modules__ = {
    "copy",
    f"{__spec__.parent}._parser",
    f"{__spec__.parent}._tokenizer",
    f"{__spec__.parent}.markers",
    f"{__spec__.parent}.specifiers",
    f"{__spec__.parent}.utils",
}

import builtins
import copy
import functools
import sys
from typing import TYPE_CHECKING, Any

from ._parser import parse_requirement as _parse_requirement
from ._tokenizer import ParserSyntaxError
from .markers import Marker, _normalize_extra_values
from .specifiers import InvalidSpecifier, SpecifierSet
from .utils import canonicalize_name

if TYPE_CHECKING:
    from collections.abc import Iterator

    from typing_extensions import Self

__all__ = [
    "InvalidRequirement",
    "Requirement",
]


def __dir__() -> list[str]:
    return __all__


# Sentinel for __replace__, typed as Any so it can be the default for any field.
# mypy is missing sentinel currently
_UNSET: Any = object() if sys.version_info < (3, 15) else builtins.sentinel("_UNSET")  # type: ignore[attr-defined]


class InvalidRequirement(ValueError):
    """
    Raised when attempting to create a :class:`Requirement` with a string that
    does not conform to the specification. Users should refer to PEP 508.

    .. versionadded:: 16.1
    .. versionchanged:: 26.4
       Added the :attr:`message`, :attr:`source`, and :attr:`span` attributes.
    """

    def __init__(
        self,
        *args: object,
        message: str | None = None,
        source: str | None = None,
        span: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(*args)
        if message is not None:
            self.message = message
        self.source: str | None = source
        """The text that failed to parse, or ``None`` if not a syntax error."""
        self.span: tuple[int, int] | None = span
        """The ``(start, end)`` indices of the error in :attr:`source`, or
        ``None`` if not a syntax error."""

    @functools.cached_property
    def message(self) -> str:
        """The error message, without the source display."""
        return super().__str__()


class Requirement:
    """Represent a requirement for a project.

    Parse a given requirement string into its parts, such as name, specifier,
    URL, and extras, according to the specification.

    .. versionadded:: 16.1

    .. versionchanged:: 22.0
        Added equality (``__eq__``) and hashing (``__hash__``) so requirements
        can be compared and stored in sets / dicts.

    .. versionchanged:: 23.2
        Equality and hashing began canonicalizing requirement names, so
        requirements whose names differ only by normalization (e.g.
        ``Requirement("Foo")`` vs ``Requirement("foo")``) now compare and hash
        equal.

    Instances are safe to serialize with :mod:`pickle`. They use a stable
    format so the same pickle can be loaded in future packaging releases.

    .. versionchanged:: 26.2

        Added a stable pickle format. Pickles created with packaging 26.2+ can
        be unpickled with future releases.  Backward compatibility with pickles
        from pip._vendor.packaging < 26.2 is supported but may be removed in a future
        release.

    .. versionchanged:: 26.3

        The dedicated pickle support introduced in 26.2 did not preserve the
        specifier's explicit :attr:`~packaging.specifiers.SpecifierSet.prereleases`
        override; it is now included again.

        Equality and hashing normalize requirement names, extras, and
        equivalent specifiers. The string representation still preserves the
        parsed name and extras spelling.

    .. versionchanged:: 26.4

        Added ``__replace__``, enabling :func:`copy.replace` on Python 3.13+.

        Pickling and copying preserve a
        :attr:`~packaging.specifiers.Specifier.prereleases` override on each
        specifier in :attr:`specifier`.

    :param str requirement_string: The string representation of a requirement.
    :raises InvalidRequirement: If the given ``requirement_string`` is not
        parseable, then this exception will be raised.
    """

    # TODO: Can we test whether something is contained within a requirement?
    #       If so how do we do that? Do we need to test against the _name_ of
    #       the thing as well as the version? What about the markers?
    # TODO: Can we normalize the name and extra name?

    __slots__ = ("extras", "marker", "name", "specifier", "url")

    def __init__(self, requirement_string: str) -> None:
        try:
            parsed = _parse_requirement(requirement_string)
        except ParserSyntaxError as e:
            raise InvalidRequirement(
                str(e), message=e.message, source=e.source, span=e.span
            ) from e

        self.name: str = parsed.name
        """The name of the requirement."""
        self.url: str | None = parsed.url or None
        """The URL to download the requirement from, or ``None``."""
        self.extras: set[str] = set(parsed.extras)
        """A set of extras that the requirement specifies."""
        try:
            self.specifier: SpecifierSet = (
                SpecifierSet(parsed.specifier)
                if isinstance(parsed.specifier, str)
                else parsed.specifier
            )
            """A :class:`~.SpecifierSet` of the version specified by the requirement."""
        except InvalidSpecifier as e:
            raise InvalidRequirement(str(e)) from e
        self.marker: Marker | None = None
        """A :class:`~.Marker` for the requirement, or ``None``."""
        if parsed.marker is not None:
            self.marker = Marker.__new__(Marker)
            self.marker._markers = _normalize_extra_values(parsed.marker)
            self.marker._serialized = None

    def __replace__(
        self,
        *,
        name: str = _UNSET,
        url: str | None = _UNSET,
        extras: set[str] = _UNSET,
        specifier: SpecifierSet = _UNSET,
        marker: Marker | None = _UNSET,
    ) -> Self:
        """Return a copy with the given fields replaced.

        This also enables :func:`copy.replace` on Python 3.13+. The result is
        validated and normalized by re-parsing its string form, so invalid
        replacements raise :exc:`InvalidRequirement`.

        .. versionadded:: 26.4
        """
        tmp = Requirement.__new__(Requirement)
        tmp.name = self.name if name is _UNSET else name
        tmp.url = self.url if url is _UNSET else url or None
        tmp.extras = self.extras if extras is _UNSET else extras
        tmp.specifier = self.specifier if specifier is _UNSET else specifier
        tmp.marker = self.marker if marker is _UNSET else marker

        result = self.__class__(str(tmp))
        # A field that parses as something more than itself (for example
        # ``name="foo[bar]"``) would silently change other fields; reject it.
        if (
            result.name != tmp.name
            or result.url != tmp.url
            or result.extras != tmp.extras
        ):
            raise InvalidRequirement(
                f"Replacement fields do not round-trip: {str(tmp)!r}"
            )
        # Specifiers technically can be mutated, so deep copy needed
        result.specifier = copy.deepcopy(tmp.specifier)
        return result

    def _iter_parts(self, name: str) -> Iterator[str]:
        yield name

        if self.extras:
            formatted_extras = ",".join(sorted(self.extras))
            yield f"[{formatted_extras}]"

        if self.specifier:
            yield str(self.specifier)

        if self.url:
            yield f" @ {self.url}"
            if self.marker:
                yield " "

        if self.marker:
            yield f"; {self.marker}"

    def __getstate__(self) -> tuple[str, bool | None, tuple[bool | None, ...]]:
        # Only primitives, for stability: the requirement string, then the
        # prereleases overrides that the string cannot hold, for the
        # SpecifierSet and for each specifier in canonical order. Re-parsed
        # on load to reconstruct all other fields.
        specs = self.specifier._canonical_specs()
        return (
            str(self),
            self.specifier._prereleases,
            tuple(s._prereleases for s in specs),
        )

    def __setstate__(self, state: object) -> None:
        inner: object = None
        prereleases: bool | None = None
        if isinstance(state, str):
            # Format (26.2): just the requirement string.
            requirement_string: str = state
        elif (
            isinstance(state, tuple)
            and len(state) in {2, 3}
            and isinstance(state[0], str)
            and (state[1] is None or isinstance(state[1], bool))
        ):
            # Format (26.3): (requirement string, specifier prereleases).
            # Format (26.4+): the same, then a tuple with the prereleases of
            # each specifier in canonical order.
            requirement_string, prereleases = state[:2]
            if len(state) == 3:
                inner = state[2]
        elif isinstance(state, dict) and state.keys() >= set(self.__slots__):
            # Old format (packaging <= 26.1, no __slots__): plain __dict__.
            for key in self.__slots__:
                setattr(self, key, state[key])
            return
        else:
            raise TypeError(f"Cannot restore Requirement from {state!r}")

        try:
            tmp = Requirement(requirement_string)
        except InvalidRequirement as exc:
            raise TypeError(f"Cannot restore Requirement from {state!r}") from exc
        if inner is not None:
            specs = tmp.specifier._canonical_specs()
            if (
                not isinstance(inner, tuple)
                or len(inner) != len(specs)
                or not all(p is None or isinstance(p, bool) for p in inner)
            ):
                raise TypeError(f"Cannot restore Requirement from {state!r}")
            for spec, spec_prereleases in zip(specs, inner, strict=True):
                spec._prereleases = spec_prereleases
        tmp.specifier._prereleases = prereleases
        self.name = tmp.name
        self.url = tmp.url
        self.extras = tmp.extras
        self.specifier = tmp.specifier
        self.marker = tmp.marker

    def __str__(self) -> str:
        return "".join(self._iter_parts(self.name))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({str(self)!r})>"

    def __hash__(self) -> int:
        # Mirror __eq__ by hashing the canonical specifier object rather than
        # its raw string. ``_iter_parts`` yields ``str(self.specifier)``, which
        # is non-canonical, so trailing-zero-equivalent requirements such as
        # ``foo==1.0.0`` and ``foo==1.0.0.0`` (which compare equal) would
        # otherwise hash differently, breaking the hash/__eq__ invariant.
        return hash(
            (
                canonicalize_name(self.name),
                frozenset(canonicalize_name(e) for e in self.extras),
                self.specifier,
                self.url,
                self.marker,
            )
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            return NotImplemented

        # Extras must be normalized before comparison as per PEP 685.
        self_extras = frozenset(canonicalize_name(e) for e in self.extras)
        other_extras = frozenset(canonicalize_name(e) for e in other.extras)
        return (
            canonicalize_name(self.name) == canonicalize_name(other.name)
            and self_extras == other_extras
            and self.specifier == other.specifier
            and self.url == other.url
            and self.marker == other.marker
        )
