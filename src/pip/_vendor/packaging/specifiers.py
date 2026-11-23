# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from pip._vendor.packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from pip._vendor.packaging.version import Version
"""

from __future__ import annotations

__lazy_modules__ = {f"{__spec__.parent}._ranges"}

import abc
import builtins
import re
import sys
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    TypeVar,
)

from ._ranges import (
    FULL_RANGE,
    IntervalIndex,
    bounds_for_spec,
    coerce_version,
    filter_by_ranges,
    index_intervals,
    intersect_specifier_bounds,
    matches_bounds_only,
    ranges_are_prerelease_only,
    resolve_prereleases,
)
from .version import Version, _adapt_possessive

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from typing import TypeGuard

    from typing_extensions import Self

    from . import ranges
    from ._ranges import Interval, SearchBounds


__all__ = [
    "BaseSpecifier",
    "InvalidSpecifier",
    "Specifier",
    "SpecifierSet",
]


def __dir__() -> list[str]:
    return __all__


def _validate_spec(spec: object, /) -> TypeGuard[tuple[str, str]]:
    return (
        isinstance(spec, tuple)
        and len(spec) == 2
        and isinstance(spec[0], str)
        and isinstance(spec[1], str)
    )


def _validate_pre(pre: object, /) -> TypeGuard[bool | None]:
    return pre is None or isinstance(pre, bool)


T = TypeVar("T")
UnparsedVersion = Version | str
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)


# Sentinel for __replace__, typed as Any so it can be the default for any field.
# mypy is missing sentinel currently
_UNSET: Any = object() if sys.version_info < (3, 15) else builtins.sentinel("_UNSET")  # type: ignore[attr-defined]


def _fast_match(specifier: Specifier, parsed: Version) -> bool | None:
    """Match ``parsed`` against ``specifier`` without building a range.

    Handles ``>=``, ``<=``, ``==``, ``!=``, ``<``, ``>`` when the spec is
    not a wildcard and ``parsed`` has no local. Returns ``None`` when the
    range path must be used: for ``===``, ``~=``, wildcards, a local
    ``parsed``, and ``<V`` where ``parsed`` has V's release and V is a final
    release with a post segment. Pre-release policy is left to the caller.

    The comparison keys are compared directly; that is what the rich
    comparisons on :class:`Version` do, without the call overhead.
    """
    op_str, ver_str = specifier._spec
    # All locals use the range path, which handles how PEP 440 strips them
    # for ``<=``/``==``/``!=``.
    if parsed._local is not None or op_str in {"~=", "==="} or ver_str.endswith(".*"):
        return None

    spec_v = specifier._spec_version or specifier._require_spec_version()

    key = parsed._key_cache or parsed._key
    spec_key = spec_v._key_cache or spec_v._key

    if op_str == ">=":
        return key >= spec_key
    if op_str == "<=":
        return key <= spec_key
    if op_str == "==":
        return key == spec_key
    if op_str == "!=":
        return key != spec_key

    # ``<V``/``>V`` carve out V's family (pre/dev/post); that only matters
    # when parsed shares V's epoch and trimmed release, the first two key
    # items. Otherwise a direct comparison is correct.
    if key[0] != spec_key[0] or key[1] != spec_key[1]:
        return key < spec_key if op_str == "<" else key > spec_key

    if op_str == "<":
        # ``<V`` is ``< V.dev0`` unless V is a pre-release. Nothing with V's
        # release sorts below a final V's ``.dev0``.
        if spec_v._pre is not None or spec_v._dev is not None:
            return key < spec_key
        return False if spec_v._post is None else None

    # Only ``>`` is left. ``>V`` excludes the post-releases of a final or
    # pre-release V; those are the later versions that share V's pre segment.
    if spec_v._dev is not None or spec_v._post is not None:
        return key > spec_key
    return key > spec_key and parsed._pre != spec_v._pre


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    """
    Abstract base class for :class:`Specifier` and :class:`SpecifierSet`.
    """

    __slots__ = ()
    __match_args__ = ("_str",)

    @property
    def _str(self) -> str:
        """Internal property for match_args"""
        return str(self)

    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> bool | None:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter  # noqa: B027
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: bool | None = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @typing.overload
    def filter(
        self,
        iterable: Iterable[UnparsedVersionVar],
        prereleases: bool | None = None,
        key: None = ...,
    ) -> Iterator[UnparsedVersionVar]: ...

    @typing.overload
    def filter(
        self,
        iterable: Iterable[T],
        prereleases: bool | None = None,
        key: Callable[[T], UnparsedVersion] = ...,
    ) -> Iterator[T]: ...

    @abc.abstractmethod
    def filter(
        self,
        iterable: Iterable[Any],
        prereleases: bool | None = None,
        key: Callable[[Any], UnparsedVersion] | None = None,
    ) -> Iterator[Any]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).

    Instances are safe to serialize with :mod:`pickle`. They use a stable
    format so the same pickle can be loaded in future packaging releases.

    .. versionchanged:: 26.2

        Added a stable pickle format. Pickles created with packaging 26.2+ can
        be unpickled with future releases.  Backward compatibility with pickles
        from pip._vendor.packaging < 26.2 is supported but may be removed in a future
        release.
    """

    __slots__ = (
        "_canonical_spec_cache",
        "_prereleases",
        "_ranges",
        "_spec",
        "_spec_version",
    )

    _specifier_regex_str = _adapt_possessive(
        r"""
        (?:
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                ===  # Only match for the identity operator
                \s*+
                [^\s;)]++ # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?:==|!=)            # Only match for equals and not equals

                \s*+
                v?+
                (?:[0-9]++!)?+          # epoch
                [0-9]++(?:\.[0-9]++)*+  # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?a:                                  # pre release
                        [-_\.]?+
                        (?:alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?+
                        [0-9]*+
                    )?+
                    (?a:                                  # post release
                        (?:-[0-9]++)|(?:[-_\.]?+(?:post|rev|r)[-_\.]?+[0-9]*+)
                    )?+
                    (?a:[-_\.]?+dev[-_\.]?+[0-9]*+)?+          # dev release
                    (?a:\+[a-z0-9]++(?:[-_\.][a-z0-9]++)*+)?+  # local
                )?+
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?:~=)               # Only match for the compatible operator

                \s*+
                v?+
                (?:[0-9]++!)?+          # epoch
                [0-9]++(?:\.[0-9]++)++  # release (We have a + instead of a *)
                (?a:                  # pre release
                    [-_\.]?+
                    (?:alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?+
                    [0-9]*+
                )?+
                (?a:                                  # post release
                    (?:-[0-9]++)|(?:[-_\.]?+(?:post|rev|r)[-_\.]?+[0-9]*+)
                )?+
                (?a:[-_\.]?+dev[-_\.]?+[0-9]*+)?+          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?:<=|>=|<|>)

                \s*+
                v?+
                (?:[0-9]++!)?+          # epoch
                [0-9]++(?:\.[0-9]++)*+  # release
                (?a:                   # pre release
                    [-_\.]?+
                    (?:alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?+
                    [0-9]*+
                )?+
                (?a:                                   # post release
                    (?:-[0-9]++)|(?:[-_\.]?+(?:post|rev|r)[-_\.]?+[0-9]*+)
                )?+
                (?a:[-_\.]?+dev[-_\.]?+[0-9]*+)?+           # dev release
            )
        )
        """
    )

    _regex = re.compile(
        r"\s*" + _specifier_regex_str + r"\s*", re.VERBOSE | re.IGNORECASE
    )

    # Legacy unused attribute, kept for backward compatibility
    _operators: Final = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: bool | None = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        if not self._regex.fullmatch(spec):
            raise InvalidSpecifier(f"Invalid specifier: {spec!r}")

        spec = spec.strip()
        if spec.startswith("==="):
            operator, version = spec[:3], spec[3:].strip()
        elif spec.startswith(("~=", "==", "!=", "<=", ">=")):
            operator, version = spec[:2], spec[2:].strip()
        else:
            operator, version = spec[:1], spec[1:].strip()

        self._spec: tuple[str, str] = (operator, version)

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

        # Specifier version cache
        self._spec_version: Version | None = None

        # Cached intervals, with an index once this specifier needs one.
        self._ranges: tuple[Interval, ...] | IntervalIndex | None = None

        # Canonical (operator, version) cache (populated by _canonical_spec)
        self._canonical_spec_cache: tuple[str, str] | None = None

    def __replace__(
        self,
        *,
        operator: str = _UNSET,
        version: str = _UNSET,
        prereleases: bool | None = _UNSET,
    ) -> Self:
        """__replace__(*, operator=..., version=..., prereleases=...)

        Return a specifier with the given parts replaced. If no part changes,
        return ``self``.

        :param str operator:
            Replacement comparison operator. Omit to retain the current operator.
        :param str version:
            Replacement version string. Omit to retain the current version.
        :param prereleases:
            Replacement prerelease override. Omit to retain the current override;
            ``None`` restores automatic detection.
        :type prereleases: bool | None

        .. versionadded:: 26.4
        """
        new_operator = self.operator if operator is _UNSET else operator
        new_version = self.version if version is _UNSET else version
        new_prereleases = self._prereleases if prereleases is _UNSET else prereleases
        if (
            new_operator == self.operator
            and new_version == self.version
            and new_prereleases == self._prereleases
        ):
            return self

        return self.__class__(
            f"{new_operator}{new_version}", prereleases=new_prereleases
        )

    def _get_spec_version(self) -> Version | None:
        """Parse and cache the spec version, without any ``.*`` suffix.

        Returns ``None`` if it is not a valid version (only for ``===``).
        """
        if (cached := self._spec_version) is not None:
            return cached

        operator, version = self._spec
        if operator != "===":
            version = version.removesuffix(".*")
        self._spec_version = coerce_version(version)
        return self._spec_version

    def _require_spec_version(self) -> Version:
        """Get spec version, asserting it's valid (not for === operator).

        This method should only be called for operators where version
        strings are guaranteed to be valid PEP 440 versions (not ===).
        """
        spec_version = self._get_spec_version()
        assert spec_version is not None
        return spec_version

    def _to_intervals(self) -> tuple[Interval, ...]:
        """Get the intervals for intersection without preparing an index."""
        ranges = self._ranges
        if ranges is None:
            op, version = self.operator, self.version
            ranges = self._ranges = (
                FULL_RANGE
                if op == "==="
                else bounds_for_spec(op, version, self._require_spec_version())
            )

        return ranges.intervals if isinstance(ranges, IntervalIndex) else ranges

    def _to_ranges(self) -> SearchBounds:
        """Prepare these intervals for direct membership checks."""
        ranges = self._ranges
        if isinstance(ranges, IntervalIndex):
            return ranges

        result = index_intervals(self._to_intervals() if ranges is None else ranges)
        self._ranges = result
        return result

    @property
    def prereleases(self) -> bool | None:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Only the "!=" operator does not imply prereleases when
        # the version in the specifier is a prerelease.
        operator, version_str = self._spec
        if operator == "!=":
            return False

        # The == specifier with trailing .* cannot include prereleases
        # e.g. "==1.0a1.*" is not valid.
        if operator == "==" and version_str.endswith(".*"):
            return False

        # "===" can have arbitrary string versions, so we cannot parse
        # those, we take prereleases as unknown (None) for those.
        version = self._get_spec_version()
        if version is None:
            return None

        # For all other operators, use the check if spec Version
        # object implies pre-releases.
        return version.is_prerelease

    @prereleases.setter
    def prereleases(self, value: bool | None) -> None:
        self._prereleases = value

    def __getstate__(self) -> tuple[tuple[str, str], bool | None]:
        # Return state as a 2-item tuple for compactness:
        #   ((operator, version), prereleases)
        # Cache members are excluded and will be recomputed on demand.
        return (self._spec, self._prereleases)

    def __setstate__(self, state: object) -> None:
        # Always discard cached values - they will be recomputed on demand.
        self._spec_version = None
        self._ranges = None
        self._canonical_spec_cache = None

        if isinstance(state, tuple):
            if len(state) == 2:
                # New format (26.2+): ((operator, version), prereleases)
                spec, prereleases = state
                if _validate_spec(spec) and _validate_pre(prereleases):
                    self._spec = spec
                    self._prereleases = prereleases
                    return
            if len(state) == 2 and isinstance(state[1], dict):
                # Format (packaging 26.0-26.1): (None, {slot: value}).
                _, slot_dict = state
                spec = slot_dict.get("_spec")
                prereleases = slot_dict.get("_prereleases", "invalid")
                if _validate_spec(spec) and _validate_pre(prereleases):
                    self._spec = spec
                    self._prereleases = prereleases
                    return
        if isinstance(state, dict):
            # Old format (packaging <= 25.x, no __slots__): state is a plain dict.
            spec = state.get("_spec")
            prereleases = state.get("_prereleases", "invalid")
            if _validate_spec(spec) and _validate_pre(prereleases):
                self._spec = spec
                self._prereleases = prereleases
                return

        raise TypeError(f"Cannot restore Specifier from {state!r}")

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        operator, version = self._spec
        return operator + version

    @property
    def _canonical_spec(self) -> tuple[str, str]:
        cached = self._canonical_spec_cache
        if cached is not None:
            return cached

        operator, version = self._spec
        if operator == "===" or version.endswith(".*"):
            result = self._spec
        else:
            spec_version = self._require_spec_version()
            canonical = str(
                spec_version if operator == "~=" else spec_version._trim_release()
            )
            # Most versions are already canonical, so reuse the existing tuple rather
            # than retaining a second copy of a string equal to the one we hold.
            result = self._spec if canonical == version else (operator, canonical)

        self._canonical_spec_cache = result
        return result

    def __hash__(self) -> int:
        # Read the cache directly to skip the property call on warm specifiers.
        if (canonical := self._canonical_spec_cache) is None:
            canonical = self._canonical_spec
        return hash(canonical)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        if (canonical := self._canonical_spec_cache) is None:
            canonical = self._canonical_spec
        if (other_canonical := other._canonical_spec_cache) is None:
            other_canonical = other._canonical_spec
        return canonical == other_canonical

    def __contains__(self, item: str | Version) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        True
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(self, item: UnparsedVersion, prereleases: bool | None = None) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`~packaging.version.Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it will follow the recommendation from
            :pep:`440` and match prereleases, as there are no other versions.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3", prereleases=False).contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        True

        .. versionchanged:: 26.0

            With ``prereleases=None``, a prerelease now matches. A single
            version has no alternatives, so the :pep:`440` rule to accept
            prereleases when nothing else satisfies the specifier applies.
            Earlier versions rejected it. An unparsable version now returns
            ``False`` instead of raising :exc:`~packaging.version.InvalidVersion`.
        """
        # ``===`` compares the raw string, so a Version parse here would
        # be wasted.
        if self._spec[0] == "===":
            return bool(list(self.filter([item], prereleases=prereleases)))

        parsed = coerce_version(item)
        if parsed is None:
            # Standard operators never match an unparsable input.
            return False

        if prereleases is None:
            prereleases = resolve_prereleases(self._prereleases, self.prereleases)

        if prereleases is False and parsed.is_prerelease:
            return False

        # ``_fast_match`` answers the simple operators without building a
        # range; otherwise fall back to the engine's bounds membership.
        match = _fast_match(self, parsed)
        if match is not None:
            return match

        return matches_bounds_only(self._to_ranges(), parsed)

    @typing.overload
    def filter(
        self,
        iterable: Iterable[UnparsedVersionVar],
        prereleases: bool | None = None,
        key: None = ...,
    ) -> Iterator[UnparsedVersionVar]: ...

    @typing.overload
    def filter(
        self,
        iterable: Iterable[T],
        prereleases: bool | None = None,
        key: Callable[[T], UnparsedVersion] = ...,
    ) -> Iterator[T]: ...

    def filter(
        self,
        iterable: Iterable[Any],
        prereleases: bool | None = None,
        key: Callable[[Any], UnparsedVersion] | None = None,
    ) -> Iterator[Any]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and
            :class:`~packaging.version.Version` instances. The items in the
            iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will follow the recommendation from :pep:`440`
            and match prereleases if there are no other versions.
        :param key:
            A callable that takes a single argument (an item from the iterable) and
            returns a version string or :class:`~packaging.version.Version`
            instance to be used for filtering.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3").filter(
        ... [{"ver": "1.2"}, {"ver": "1.3"}],
        ... key=lambda x: x["ver"]))
        [{'ver': '1.3'}]

        .. versionchanged:: 26.1

            Added the ``key`` parameter.
        """
        if prereleases is None:
            prereleases = resolve_prereleases(self._prereleases, self.prereleases)

        if self.operator == "===":
            spec_lower = self.version.lower()
            matches = (
                item
                for item in iterable
                if str(item if key is None else key(item)).lower() == spec_lower
            )
            return _apply_prereleases_filter(matches, key, prereleases)

        return filter_by_ranges(self._to_ranges(), iterable, key, prereleases)


def _apply_prereleases_filter(
    matches: Iterable[Any],
    key: Callable[[Any], UnparsedVersion] | None,
    prereleases: bool | None,
) -> Iterator[Any]:
    """Apply ``prereleases=`` handling to an already-matched iterable.

    ``None`` means PEP 440 default (buffer pre-releases until a final
    appears); ``True`` yields everything; ``False`` drops pre-releases.
    """
    if prereleases is None:
        return _pep440_filter_prereleases(matches, key)
    if prereleases:
        return iter(matches)
    return (
        item
        for item in matches
        if (parsed := coerce_version(item if key is None else key(item))) is None
        or not parsed.is_prerelease
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.

    Instances are safe to serialize with :mod:`pickle`. They use a stable
    format so the same pickle can be loaded in future packaging
    releases.

    .. versionchanged:: 26.2

        Added a stable pickle format. Pickles created with
        packaging 26.2+ can be unpickled with future releases.
        Backward compatibility with pickles from
        packaging < 26.2 is supported but may be removed in a future
        release.
    """

    __slots__ = (
        "_canonicalized",
        "_has_arbitrary",
        "_is_unsatisfiable",
        "_prereleases",
        "_ranges",
        "_specs",
    )

    def __init__(
        self,
        specifiers: str | Iterable[Specifier | str] = "",
        prereleases: bool | None = None,
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
            May also be an iterable of ``Specifier`` instances, which will be used
            as is. Plain ``str`` elements are parsed as if passed to
            :class:`Specifier`, so ``SpecifierSet([">=1.0"])`` equals
            ``SpecifierSet(">=1.0")``.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        :raises TypeError:
            If an element of the iterable form is neither a :class:`Specifier`
            nor a ``str``.
        """

        if isinstance(specifiers, str):
            # Split on `,` to break each individual specifier into its own item, and
            # strip each item to remove leading/trailing whitespace.
            split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

            self._specs: tuple[Specifier, ...] = tuple(map(Specifier, split_specifiers))
            # Fast substring check; avoids iterating parsed specs.
            self._has_arbitrary = "===" in specifiers
        else:
            # List comprehension is faster than generator below
            self._specs = tuple(
                [s if isinstance(s, Specifier) else Specifier(s) for s in specifiers]
            )
            self._has_arbitrary = any(s.operator == "===" for s in self._specs)

        self._canonicalized = len(self._specs) <= 1
        self._is_unsatisfiable: bool | None = None
        self._ranges: SearchBounds | None = None

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    def __replace__(
        self,
        *,
        specifiers: str | Iterable[Specifier | str] = _UNSET,
        prereleases: bool | None = _UNSET,
    ) -> Self:
        """__replace__(*, specifiers=..., prereleases=...)

        Return a specifier set with the given parts replaced. If ``specifiers``
        is omitted and the prerelease override is unchanged, return ``self``.

        :param specifiers:
            Replacement specifiers as a string or an iterable of ``Specifier``
            and ``str`` instances. Omit to retain the current specifiers.
        :type specifiers: str | Iterable[Specifier | str]
        :param prereleases:
            Replacement prerelease override. Omit to retain the current override;
            ``None`` restores automatic detection.
        :type prereleases: bool | None

        .. versionadded:: 26.4
        """
        new_specifiers = self._specs if specifiers is _UNSET else specifiers
        new_prereleases = self._prereleases if prereleases is _UNSET else prereleases
        if specifiers is _UNSET and new_prereleases == self._prereleases:
            return self

        return self.__class__(new_specifiers, prereleases=new_prereleases)

    def _canonical_specs(self) -> tuple[Specifier, ...]:
        """Deduplicate, sort, and cache specs for order-sensitive operations."""
        if not self._canonicalized:
            self._specs = tuple(dict.fromkeys(sorted(self._specs, key=str)))
            self._canonicalized = True
        return self._specs

    @property
    def prereleases(self) -> bool | None:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        if any(s.prereleases for s in self._specs):
            return True

        return None

    @prereleases.setter
    def prereleases(self, value: bool | None) -> None:
        self._prereleases = value
        self._is_unsatisfiable = None

    def __getstate__(self) -> tuple[tuple[Specifier, ...], bool | None]:
        # Return state as a 2-item tuple for compactness:
        #   (specs, prereleases)
        # Cache members are excluded and will be recomputed on demand.
        return (self._specs, self._prereleases)

    def __setstate__(self, state: object) -> None:
        # Always discard cached values - they will be recomputed on demand.
        self._ranges = None
        self._is_unsatisfiable = None

        if isinstance(state, tuple):
            if len(state) == 2:
                # New format (26.2+): (specs, prereleases)
                specs, prereleases = state
                if (
                    isinstance(specs, tuple)
                    and all(isinstance(s, Specifier) for s in specs)
                    and _validate_pre(prereleases)
                ):
                    self._specs = specs
                    self._prereleases = prereleases
                    self._canonicalized = len(specs) <= 1
                    self._has_arbitrary = any("===" in str(s) for s in specs)
                    return
            if len(state) == 2 and isinstance(state[1], dict):
                # Format (packaging 26.0-26.1): (None, {slot: value}).
                _, slot_dict = state
                specs = slot_dict.get("_specs", ())
                prereleases = slot_dict.get("_prereleases")
                # Convert frozenset to tuple (26.0 stored as frozenset)
                if isinstance(specs, frozenset):
                    specs = tuple(sorted(specs, key=str))
                if (
                    isinstance(specs, tuple)
                    and all(isinstance(s, Specifier) for s in specs)
                    and _validate_pre(prereleases)
                ):
                    self._specs = specs
                    self._prereleases = prereleases
                    self._canonicalized = len(self._specs) <= 1
                    self._has_arbitrary = any("===" in str(s) for s in self._specs)
                    return
        if isinstance(state, dict):
            # Old format (packaging <= 25.x, no __slots__): state is a plain dict.
            specs = state.get("_specs", ())
            prereleases = state.get("_prereleases")
            # Convert frozenset to tuple (26.0 stored as frozenset)
            if isinstance(specs, frozenset):
                specs = tuple(sorted(specs, key=str))
            if (
                isinstance(specs, tuple)
                and all(isinstance(s, Specifier) for s in specs)
                and _validate_pre(prereleases)
            ):
                self._specs = specs
                self._prereleases = prereleases
                self._canonicalized = len(self._specs) <= 1
                self._has_arbitrary = any("===" in str(s) for s in self._specs)
                return

        raise TypeError(f"Cannot restore SpecifierSet from {state!r}")

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(str(s) for s in self._canonical_specs())

    def __hash__(self) -> int:
        return hash(self._canonical_specs())

    def __and__(self, other: SpecifierSet | str) -> SpecifierSet:
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = self._specs + other._specs
        specifier._canonicalized = len(specifier._specs) <= 1
        specifier._has_arbitrary = self._has_arbitrary or other._has_arbitrary

        # Combine prerelease settings: use common or non-None value
        if self._prereleases is None or self._prereleases == other._prereleases:
            specifier._prereleases = other._prereleases
        elif other._prereleases is None:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._canonical_specs() == other._canonical_specs()

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def _get_ranges(self) -> SearchBounds:
        """Return the search bounds shared by all specifiers in this set.

        Empty when unsatisfiable. Callers must ensure ``self._specs``
        is non-empty.
        """
        if self._ranges is not None:
            return self._ranges

        if len(self._specs) == 1:
            self._ranges = self._specs[0]._to_ranges()
        else:
            self._ranges = intersect_specifier_bounds(
                s._to_intervals() for s in self._specs
            )
        return self._ranges

    def is_unsatisfiable(self) -> bool:
        """Check whether this specifier set can never be satisfied.

        Returns True if no version can satisfy all specifiers simultaneously.

        >>> SpecifierSet(">=2.0,<1.0").is_unsatisfiable()
        True
        >>> SpecifierSet(">=1.0,<2.0").is_unsatisfiable()
        False
        >>> SpecifierSet("").is_unsatisfiable()
        False
        >>> SpecifierSet("==1.0,!=1.0").is_unsatisfiable()
        True

        .. versionadded:: 26.1
        """
        cached = self._is_unsatisfiable
        if cached is not None:
            return cached

        if not self._specs:
            self._is_unsatisfiable = False
            return False

        result = not self._get_ranges()

        if not result:
            result = self._check_arbitrary_unsatisfiable()

        if not result and self.prereleases is False:
            result = ranges_are_prerelease_only(self._get_ranges())

        self._is_unsatisfiable = result
        return result

    def _check_arbitrary_unsatisfiable(self) -> bool:
        """Check === (arbitrary equality) specs for unsatisfiability.

        === uses case-insensitive string comparison, so the only candidate
        that can match ``===V`` is the literal string V.  This method
        checks whether that candidate is excluded by other specifiers.
        """
        arbitrary = [s for s in self._specs if s.operator == "==="]
        if not arbitrary:
            return False

        # Multiple === must agree on the same string (case-insensitive).
        first = arbitrary[0].version.lower()
        if any(s.version.lower() != first for s in arbitrary[1:]):
            return True

        # The sole candidate is the === version string.  Check whether
        # it can satisfy every standard spec.
        candidate = coerce_version(arbitrary[0].version)

        # With prereleases=False, a prerelease candidate is excluded
        # by contains() before the === string check even runs.
        if (
            self.prereleases is False
            and candidate is not None
            and candidate.is_prerelease
        ):
            return True

        standard = [s for s in self._specs if s.operator != "==="]
        if not standard:
            return False

        if candidate is None:
            # Unparsable string cannot satisfy any standard spec.
            return True

        return not all(s.contains(candidate) for s in standard)

    def to_range(self) -> ranges.VersionRange:
        """Return the :class:`~packaging.ranges.VersionRange` this set accepts.

        An empty set yields the full range; an unsatisfiable set yields the
        empty range. ``===`` specifiers contribute literal-string admission.

        >>> SpecifierSet(">=1.0,<2.0").to_range()
        <VersionRange '[1.0, 2.0.dev0)'>

        .. versionadded:: 26.3
        """
        from .ranges import VersionRange  # noqa: PLC0415

        return VersionRange._from_specifier_set(self)

    def _check_relation_operand(self, other: object) -> None:
        if not isinstance(other, SpecifierSet):
            raise TypeError("expected a SpecifierSet")
        if self._has_arbitrary or other._has_arbitrary:
            raise ValueError("set relations do not support === specifiers")

    def is_subset(self, other: SpecifierSet) -> bool:
        """Return whether every version matching this set also matches other.

        :raises ValueError:
            If either set uses ``===`` specifiers, or the two sets were
            given different ``prereleases`` arguments (unset on one side
            counts as different).
        :raises TypeError:
            If other is not a :class:`SpecifierSet`.

        >>> SpecifierSet(">=3.12,<3.13").is_subset(SpecifierSet(">=3.12"))
        True
        >>> SpecifierSet(">=3.12").is_subset(SpecifierSet(">=3.12,<3.13"))
        False

        .. versionadded:: 26.3
        """
        self._check_relation_operand(other)
        return self.to_range().is_subset(other.to_range())

    def is_superset(self, other: SpecifierSet) -> bool:
        """Return whether every version matching other also matches this set.

        :raises ValueError:
            If either set uses ``===`` specifiers, or the two sets were
            given different ``prereleases`` arguments (unset on one side
            counts as different).
        :raises TypeError:
            If other is not a :class:`SpecifierSet`.

        >>> SpecifierSet(">=3.12").is_superset(SpecifierSet(">=3.12,<3.13"))
        True

        .. versionadded:: 26.3
        """
        self._check_relation_operand(other)
        return self.to_range().is_superset(other.to_range())

    def is_disjoint(self, other: SpecifierSet) -> bool:
        """Return whether this set and other share no matching versions.

        :raises ValueError:
            If either set uses ``===`` specifiers, or the two sets were
            given different ``prereleases`` arguments (unset on one side
            counts as different).
        :raises TypeError:
            If other is not a :class:`SpecifierSet`.

        >>> SpecifierSet("<3.12").is_disjoint(SpecifierSet(">=3.12"))
        True
        >>> SpecifierSet("<3.12").is_disjoint(SpecifierSet(">=3.11"))
        False

        .. versionadded:: 26.3
        """
        self._check_relation_operand(other)
        return self.to_range().is_disjoint(other.to_range())

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`~packaging.version.Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it will follow the recommendation from :pep:`440`
            and match prereleases, as there are no other versions.
        :param installed:
            Whether or not the item is installed. If set to ``True``, it will
            accept prerelease versions even if the specifier does not allow them.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False).contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True

        .. versionchanged:: 26.0

            With ``prereleases=None``, a prerelease now matches. A single
            version has no alternatives, so the :pep:`440` rule to accept
            prereleases when nothing else satisfies the specifiers applies.
            Earlier versions rejected it. An unparsable version now returns
            ``False`` instead of raising :exc:`~packaging.version.InvalidVersion`.
        """
        version = item if isinstance(item, Version) else coerce_version(item)

        if installed and version is not None and version.is_prerelease:
            prereleases = True

        # When item is a string and === is involved, keep it as-is
        # so the comparison isn't done against the normalized form.
        if version is None or (self._has_arbitrary and not isinstance(item, Version)):
            check_item = item
        else:
            check_item = version

        # Fast path: a parseable version against a rangelike set.
        if version is not None and not self._has_arbitrary and self._specs:
            if (version._pre is not None or version._dev is not None) and (
                prereleases is False
                or (prereleases is None and self._prereleases is False)
            ):
                return False

            bounds = self._ranges
            if bounds is None:
                # Per-spec ``_fast_match`` answers a set of simple specifiers
                # without folding anything. If a spec needs the range path,
                # fold the intersected bounds once and cache them so repeated
                # checks on the same set stay cheap.
                for spec in self._specs:
                    match = _fast_match(spec, version)
                    if match is None:
                        break
                    if not match:
                        return False
                else:
                    return True

                bounds = self._ranges = self._get_ranges()

            return matches_bounds_only(bounds, version)

        return bool(list(self.filter([check_item], prereleases=prereleases)))

    @typing.overload
    def filter(
        self,
        iterable: Iterable[UnparsedVersionVar],
        prereleases: bool | None = None,
        key: None = ...,
    ) -> Iterator[UnparsedVersionVar]: ...

    @typing.overload
    def filter(
        self,
        iterable: Iterable[T],
        prereleases: bool | None = None,
        key: Callable[[T], UnparsedVersion] = ...,
    ) -> Iterator[T]: ...

    def filter(
        self,
        iterable: Iterable[Any],
        prereleases: bool | None = None,
        key: Callable[[Any], UnparsedVersion] | None = None,
    ) -> Iterator[Any]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and
            :class:`~packaging.version.Version` instances. The items in the
            iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will follow the recommendation from :pep:`440`
            and match prereleases if there are no other versions.
        :param key:
            A callable that takes a single argument (an item from the iterable) and
            returns a version string or :class:`~packaging.version.Version`
            instance to be used for filtering.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3").filter(
        ... [{"ver": "1.2"}, {"ver": "1.3"}],
        ... key=lambda x: x["ver"]))
        [{'ver': '1.3'}]

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']

        .. versionchanged:: 26.0

            Prerelease filtering now follows the PEP 440 recommendation of
            yielding prereleases only when no final release is present.

        .. versionchanged:: 26.1

            Added the ``key`` parameter.
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None and self.prereleases is not None:
            prereleases = self.prereleases

        if self._specs:
            if self._has_arbitrary:
                # Slow path for ===
                specs = self._specs
                matches = (
                    item
                    for item in iterable
                    if all(
                        s.contains(item if key is None else key(item), prereleases=True)
                        for s in specs
                    )
                )
                return _apply_prereleases_filter(matches, key, prereleases)

            ranges = self._ranges
            if ranges is None:
                ranges = self._get_ranges()
            return filter_by_ranges(ranges, iterable, key, prereleases)

        # Empty SpecifierSet.
        return _apply_prereleases_filter(iterable, key, prereleases)


def _pep440_filter_prereleases(
    iterable: Iterable[Any], key: Callable[[Any], UnparsedVersion] | None
) -> Iterator[Any]:
    """Filter per PEP 440: exclude prereleases unless no finals exist."""
    # Two lists used:
    #   * all_nonfinal to preserve order if no finals exist
    #   * arbitrary_strings for streaming when first final found
    all_nonfinal: list[Any] = []
    arbitrary_strings: list[Any] = []

    found_final = False
    for item in iterable:
        parsed = coerce_version(item if key is None else key(item))

        if parsed is None:
            # Arbitrary strings are always included as it is not
            # possible to determine if they are prereleases,
            # and they have already passed all specifiers.
            if found_final:
                yield item
            else:
                arbitrary_strings.append(item)
                all_nonfinal.append(item)
            continue

        if not parsed.is_prerelease:
            # Final release found - flush arbitrary strings, then yield
            if not found_final:
                yield from arbitrary_strings
                found_final = True
            yield item
            continue

        # Prerelease - buffer if no finals yet, otherwise skip
        if not found_final:
            all_nonfinal.append(item)

    # No finals found - yield all buffered items
    if not found_final:
        yield from all_nonfinal
