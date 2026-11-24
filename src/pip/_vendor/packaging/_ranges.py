# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""Private version-range helpers used by :mod:`packaging.specifiers`."""

from __future__ import annotations

__lazy_modules__ = {"bisect"}

import enum
import functools
from bisect import bisect_right
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
)

from .version import InvalidVersion, Version

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

    # Boundary keys sort alongside Version._key. A boundary after all post
    # releases uses infinity in place of a post-release number.
    _BoundaryOrderSuffix = tuple[int, int, int, int | float, int, int]
    _BoundaryOrderKey = tuple[
        int, tuple[int, ...], _BoundaryOrderSuffix, tuple[tuple[float, str], ...]
    ]

__all__ = [
    "FULL_RANGE",
    "bounds_for_spec",
    "coerce_version",
    "filter_by_ranges",
    "first_version_after_locals",
    "index_intervals",
    "intersect_ranges",
    "intersect_specifier_bounds",
    "matches_bounds_only",
    "range_is_empty",
    "ranges_are_disjoint",
    "ranges_are_prerelease_only",
    "resolve_prereleases",
    "standard_ranges",
    "wildcard_ranges",
]

#: The smallest possible PEP 440 version. No valid version is less than this.
MIN_VERSION: Final[Version] = Version("0.dev0")

#: The smallest non-pre-release version, i.e. the nearest non-pre-release at or
#: above the ``-inf`` floor.
MIN_RELEASE: Final[Version] = Version("0")

#: Sorts above any real post number and any local label, so a boundary can be
#: ordered above the version family it covers when two boundaries are compared.
_BOUNDARY_INF: Final[float] = float("inf")

#: Sorts after every local label, including numeric ones like +999.
_AFTER_LOCALS: Final = ((_BOUNDARY_INF, ""),)


class BoundaryKind(enum.Enum):
    """Where a boundary marker sits in the version ordering."""

    AFTER_LOCALS = enum.auto()  # after V+local, before V.post0
    AFTER_POSTS = enum.auto()  # after V.postN, before next release


@functools.total_ordering
class BoundaryVersion:
    """A point on the version line between two real PEP 440 versions.

    Relative to a base version V::

        V < V+local < AFTER_LOCALS(V) < V.post0 < AFTER_POSTS(V)

    AFTER_LOCALS is the upper bound of ``<=V``, ``==V``, ``!=V`` (no
    local), and the lower bound of the upper-side range of ``!=V``.
    AFTER_POSTS is the lower bound of ``>V`` (V final or pre-release),
    excluding V's post-releases per PEP 440.
    """

    __slots__ = ("_cached_successor", "_key", "kind", "version")

    # range_is_empty must check the next real version above a synthetic boundary.
    _key_cache: None = None

    def __init__(self, version: Version, kind: BoundaryKind) -> None:
        self.version = version
        self.kind = kind
        self._cached_successor: Version | None = None

        version_key = version._key
        suffix: _BoundaryOrderSuffix = version_key[2]
        if kind is BoundaryKind.AFTER_POSTS:
            # For >1, every 1.postN must sort below the boundary.
            suffix = (suffix[0], suffix[1], 1, _BOUNDARY_INF, 1, 0)

        self._key: _BoundaryOrderKey = (
            version_key[0],
            version_key[1],
            suffix,
            _AFTER_LOCALS,
        )

    @property
    def successor(self) -> Version | None:
        """The smallest real version above this boundary, if one exists."""
        if self._cached_successor is not None:
            return self._cached_successor

        if self.kind is BoundaryKind.AFTER_LOCALS:
            self._cached_successor = first_version_after_locals(self.version)
        elif self.version.pre is not None:
            # The first version after 1a1 and all its post-releases is 1a2.dev0.
            tag, number = self.version.pre
            self._cached_successor = self.version.__replace__(
                pre=(tag, number + 1), post=None, dev=0, local=None
            )

        return self._cached_successor

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BoundaryVersion):
            return self._key == other._key
        return NotImplemented

    def __lt__(self, other: BoundaryVersion | Version) -> bool:
        return self._key < other._key

    def __gt__(self, other: BoundaryVersion | Version) -> bool:
        return self._key > other._key

    def __hash__(self) -> int:
        return hash(self._key)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.version!r}, {self.kind.name})"


if TYPE_CHECKING:
    _VersionOrBoundary = Version | BoundaryVersion | None


class _Bound:
    """An interval endpoint with a reusable comparison key."""

    __slots__ = ("_filter_key", "inclusive", "version")

    def __init__(self, version: _VersionOrBoundary, inclusive: bool) -> None:
        # An unbounded end has no version to include.
        self.version = version
        self.inclusive = version is not None and inclusive

        self._filter_key: tuple[Any, ...] | None = None

    def filter_key(self) -> tuple[Any, ...]:
        """Return the point where versions start or stop matching this bound."""
        key = self._filter_key
        if key is not None:
            return key

        version = self.version
        if version is None:
            key = (
                (-_BOUNDARY_INF,) if isinstance(self, LowerBound) else (_BOUNDARY_INF,)
            )
        elif isinstance(version, BoundaryVersion):
            key = version._key
        else:
            key = version._key_cache or version._key

            # Move an excluded start or an included end just past the version.
            if isinstance(self, LowerBound):
                after_version = not self.inclusive
            else:
                after_version = self.inclusive

            if after_version:
                key = (*key, ())

        self._filter_key = key
        return key


@functools.total_ordering
class LowerBound(_Bound):
    """Lower bound of a version range.

    A version *v* of ``None`` means unbounded below (-inf), with
    ``inclusive`` forced to ``False``.
    At equal versions, ``[v`` sorts before ``(v`` because an inclusive
    bound starts earlier.
    """

    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LowerBound):
            return NotImplemented
        return self.version == other.version and self.inclusive == other.inclusive

    def __lt__(self, other: LowerBound) -> bool:
        if not isinstance(other, LowerBound):
            return NotImplemented
        # -inf < anything (except -inf itself).
        if self.version is None:
            return other.version is not None
        if other.version is None:
            return False

        # Use cached keys when both exist; cold versions and boundaries use operators.
        self_key = self.version._key_cache
        other_key = other.version._key_cache
        if self_key is None or other_key is None:
            if self.version != other.version:
                return self.version < other.version
        elif self_key != other_key:
            return self_key < other_key

        # [v < (v: inclusive starts earlier.
        return self.inclusive and not other.inclusive

    # Explicit operators avoid total_ordering's repeated comparison dispatch.
    def __gt__(self, other: LowerBound) -> bool:
        if not isinstance(other, LowerBound):
            return NotImplemented
        if self.version is None:
            return False
        if other.version is None:
            return True

        self_key = self.version._key_cache
        other_key = other.version._key_cache
        if self_key is None or other_key is None:
            if self.version != other.version:
                return other.version < self.version
        elif self_key != other_key:
            return other_key < self_key

        return other.inclusive and not self.inclusive

    def __le__(self, other: LowerBound) -> bool:
        if not isinstance(other, LowerBound):
            return NotImplemented
        if self.version is None:
            return True
        if other.version is None:
            return False

        self_key = self.version._key_cache
        other_key = other.version._key_cache
        if self_key is None or other_key is None:
            if self.version != other.version:
                return self.version < other.version
        elif self_key != other_key:
            return self_key < other_key

        return self.inclusive or not other.inclusive

    def __hash__(self) -> int:
        return hash((self.version, self.inclusive))

    def __repr__(self) -> str:
        bracket = "[" if self.inclusive else "("
        return f"<{self.__class__.__name__} {bracket}{self.version!r}>"


@functools.total_ordering
class UpperBound(_Bound):
    """Upper bound of a version range.

    A version *v* of ``None`` means unbounded above (+inf), with
    ``inclusive`` forced to ``False``.
    At equal versions, ``v)`` sorts before ``v]`` because an exclusive
    bound ends earlier.
    """

    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UpperBound):
            return NotImplemented
        return self.version == other.version and self.inclusive == other.inclusive

    def __lt__(self, other: UpperBound) -> bool:
        if not isinstance(other, UpperBound):
            return NotImplemented
        # An unbounded upper endpoint does not sort before any endpoint.
        if self.version is None:
            return False
        if other.version is None:
            return True

        # Use cached keys when both exist; cold versions and boundaries use operators.
        self_key = self.version._key_cache
        other_key = other.version._key_cache
        if self_key is None or other_key is None:
            if self.version != other.version:
                return self.version < other.version
        elif self_key != other_key:
            return self_key < other_key

        # v) < v]: exclusive ends earlier.
        return not self.inclusive and other.inclusive

    def __gt__(self, other: UpperBound) -> bool:
        if not isinstance(other, UpperBound):
            return NotImplemented
        if self.version is None:
            return other.version is not None
        if other.version is None:
            return False

        self_key = self.version._key_cache
        other_key = other.version._key_cache
        if self_key is None or other_key is None:
            if self.version != other.version:
                return other.version < self.version
        elif self_key != other_key:
            return other_key < self_key

        return self.inclusive and not other.inclusive

    def __hash__(self) -> int:
        return hash((self.version, self.inclusive))

    def __repr__(self) -> str:
        bracket = "]" if self.inclusive else ")"
        return f"<{self.__class__.__name__} {self.version!r}{bracket}>"


if TYPE_CHECKING:
    #: A single contiguous interval as a (lower, upper) bound pair.
    Interval = tuple[LowerBound, UpperBound]


def _interval_start(interval: Interval) -> tuple[Any, ...]:
    return interval[0].filter_key()


class IntervalIndex:
    """Cache searches over an immutable tuple of disjoint intervals."""

    __slots__ = ("_edges", "_estimated_probes", "intervals")

    def __init__(self, intervals: tuple[Interval, ...]) -> None:
        self.intervals = intervals

        self._edges: tuple[tuple[Any, ...], ...] = ()
        self._estimated_probes = 0

    def __iter__(self) -> Iterator[Interval]:
        return iter(self.intervals)

    def __len__(self) -> int:
        return len(self.intervals)

    def contains(self, version: Version) -> bool:
        intervals = self.intervals
        if not intervals:
            return False

        key = version._key_cache or version._key
        edges = self._edges

        if not edges:
            lower, upper = intervals[0]
            if key < upper.filter_key():
                return lower.filter_key() <= key

            # Estimate how many interval starts the binary searches have visited.
            size = len(intervals)
            probes = self._estimated_probes + size.bit_length()

            if probes < size:
                self._estimated_probes = probes
                index = bisect_right(intervals, key, lo=1, key=_interval_start) - 1
                _, upper = intervals[index]
                return key < upper.filter_key()

            # Build the table once those searches add up to a full pass.
            edges = tuple(
                bound.filter_key() for interval in intervals for bound in interval
            )
            self._edges = edges

        # Each start enters an interval and each end leaves it. An odd count matches.
        return bisect_right(edges, key) % 2 == 1


if TYPE_CHECKING:
    SearchBounds = tuple[Interval] | IntervalIndex


def index_intervals(intervals: Sequence[Interval]) -> SearchBounds:
    """Keep a single interval as a plain tuple for direct comparisons."""
    bounds = tuple(intervals)
    return bounds if len(bounds) == 1 else IntervalIndex(bounds)


NEG_INF: Final[LowerBound] = LowerBound(None, False)
POS_INF: Final[UpperBound] = UpperBound(None, False)
FULL_RANGE: Final[tuple[Interval]] = ((NEG_INF, POS_INF),)


def trim_release(release: tuple[int, ...]) -> tuple[int, ...]:
    """Strip trailing zeros from a release tuple for normalized comparison."""
    end = len(release)
    while end > 1 and release[end - 1] == 0:
        end -= 1
    return release if end == len(release) else release[:end]


def _next_prefix_dev0(version: Version) -> Version:
    """Smallest version in the next prefix: 1.2 -> 1.3.dev0."""
    release = (*version.release[:-1], version.release[-1] + 1)
    return Version.from_parts(epoch=version.epoch, release=release, dev=0)


def _base_dev0(version: Version) -> Version:
    """The .dev0 of a version's base release: 1.2 -> 1.2.dev0."""
    return Version.from_parts(epoch=version.epoch, release=version.release, dev=0)


def coerce_version(version: Version | str) -> Version | None:
    if not isinstance(version, Version):
        try:
            version = Version(version)
        except InvalidVersion:
            return None
    return version


def first_version_after_locals(version: Version) -> Version:
    """The first version above *version* and all its local versions."""
    if version.dev is not None:
        return version.__replace__(dev=version.dev + 1, local=None)

    next_post = version.post + 1 if version.post is not None else 0
    return version.__replace__(post=next_post, dev=0, local=None)


def range_is_empty(lower: LowerBound, upper: UpperBound) -> bool:
    """True when the range defined by *lower* and *upper* contains no versions.

    A boundary lower sits just below the next real version, so an ordered pair
    is still empty when the upper excludes that least successor:
    ``(AFTER_POSTS(1.0a1), 1.0a2.dev0)`` holds no version.
    """
    upper_version = upper.version
    if upper_version is None:
        return False

    lower_version = lower.version
    if lower_version is None:
        # Nothing sorts below MIN_VERSION, so an exclusive upper at or below it
        # leaves an empty floor interval such as ``(-inf, 0.dev0)``.
        return (
            not upper.inclusive
            and isinstance(upper_version, Version)
            and upper_version <= MIN_VERSION
        )

    lower_key = lower_version._key_cache
    upper_key = upper_version._key_cache
    if lower_key is not None and upper_key is not None:
        if lower.inclusive and upper.inclusive:
            return lower_key > upper_key
        return lower_key >= upper_key

    if isinstance(lower_version, BoundaryVersion):
        successor = lower_version.successor
        if successor is not None:
            if upper_version == successor:
                return not upper.inclusive
            return upper_version < successor

    if lower_version == upper_version:
        return not (lower.inclusive and upper.inclusive)

    return lower_version > upper_version


def intersect_ranges(
    left: Sequence[Interval],
    right: Sequence[Interval],
) -> list[Interval]:
    """Intersect two sorted, non-overlapping range lists (two-pointer merge)."""
    result: list[Interval] = []
    left_index = right_index = 0
    while left_index < len(left) and right_index < len(right):
        left_lower, left_upper = left[left_index]
        right_lower, right_upper = right[right_index]

        lower = max(left_lower, right_lower)

        # The earlier end closes the intersection and advances that side.
        if right_upper < left_upper:
            upper = right_upper
            right_index += 1
        else:
            upper = left_upper
            left_index += 1

        if not range_is_empty(lower, upper):
            result.append((lower, upper))

    return result


def ranges_are_disjoint(left: Sequence[Interval], right: Sequence[Interval]) -> bool:
    """Test whether two sorted, non-overlapping interval lists are disjoint.

    Each interval must contain at least one version; empty input lists are allowed.
    """
    left_index = right_index = 0
    while left_index < len(left) and right_index < len(right):
        left_lower, left_upper = left[left_index]
        right_lower, right_upper = right[right_index]

        if range_is_empty(left_lower, right_upper):
            right_index += 1
        elif range_is_empty(right_lower, left_upper):
            left_index += 1
        else:
            return False

    return True


def filter_by_ranges(
    ranges: SearchBounds,
    iterable: Iterable[Any],
    key: Callable[[Any], Version | str] | None,
    prereleases: bool | None,
    region: Sequence[Interval] = (),
) -> Iterator[Any]:
    """Filter *iterable* against precomputed version *ranges*.

    With ``prereleases=None``, the PEP 440 default applies: pre-releases are
    excluded unless no final matches, in which case buffered pre-releases come
    out at the end. A pre-release inside the opt-in ``region`` is the exception:
    it is force-admitted in place, as ``prereleases=True`` would yield it. A
    force-admitted pre-release is not a final, so it never suppresses the buffer.
    """
    if isinstance(ranges, tuple):
        indexed: IntervalIndex | None = None
        ((lower, upper),) = ranges
        floor = (
            (lower._filter_key or lower.filter_key())
            if lower.version is not None
            else None
        )
        ceiling = (
            (upper._filter_key or upper.filter_key())
            if upper.version is not None
            else None
        )
    else:
        indexed = ranges
        edges = indexed._edges

    if prereleases is None:
        prerelease_buffer: list[Any] = []
        found_final = False

    for item in iterable:
        parsed = item if key is None else key(item)
        if not isinstance(parsed, Version):
            parsed = coerce_version(parsed)
            if parsed is None:
                continue
        if prereleases is False and parsed.is_prerelease:
            continue

        if indexed is None:
            if floor is not None and (parsed._key_cache or parsed._key) < floor:
                continue
            if ceiling is not None and (parsed._key_cache or parsed._key) >= ceiling:
                continue
        elif edges:
            # Search the saved keys directly for the rest of this batch.
            if bisect_right(edges, parsed._key_cache or parsed._key) % 2 == 0:
                continue
        else:
            matches = indexed.contains(parsed)
            edges = indexed._edges
            if not matches:
                continue

        if prereleases is not None:
            yield item
        elif not parsed.is_prerelease:
            found_final = True
            yield item
        elif region and matches_bounds_only(region, parsed):
            yield item
        elif not found_final:
            prerelease_buffer.append(item)

    if prereleases is None and not found_final:
        yield from prerelease_buffer


def _nearest_release_above_prerelease(version: Version) -> Version:
    """Smallest non-pre-release at or above a pre-release *version*."""
    if version.pre is not None:
        # An a/b/rc pre-release drops to its final release, which outranks
        # every post-release of that pre-release (1.0a1.post0 -> 1.0).
        return version.__replace__(pre=None, post=None, dev=None, local=None)

    # A dev-only release keeps its post-release (1.0.post0.dev0 -> 1.0.post0,
    # whose final 1.0 sorts below it).
    return version.__replace__(dev=None, local=None)


def _lowest_release_at_or_above(value: Version | BoundaryVersion | None) -> Version:
    """Smallest non-pre-release version at or above *value*.

    ``None`` is the ``-inf`` floor, whose nearest non-pre-release is
    :data:`MIN_RELEASE`.
    """
    if value is None:
        return MIN_RELEASE
    if isinstance(value, BoundaryVersion):
        inner_version = value.version
        if inner_version.is_prerelease:
            return _nearest_release_above_prerelease(inner_version)
        # AFTER_LOCALS(1.0) -> nearest non-pre is 1.0.post0
        # AFTER_LOCALS(1.0.post0) -> nearest non-pre is 1.0.post1
        next_post = (inner_version.post + 1) if inner_version.post is not None else 0
        return inner_version.__replace__(post=next_post, local=None)

    if not value.is_prerelease:
        return value

    return _nearest_release_above_prerelease(value)


def ranges_are_prerelease_only(ranges: Iterable[Interval]) -> bool:
    """True when every range in *ranges* contains only pre-releases.

    Used to detect unsatisfiable specifier sets when ``prereleases=False``:
    if every range is pre-release-only, every contained version is excluded.
    """
    for lower, upper in ranges:
        nearest = _lowest_release_at_or_above(lower.version)
        if upper.version is None or nearest < upper.version:
            return False
        if nearest == upper.version and upper.inclusive:
            return False
    return True


def wildcard_ranges(op: str, base: Version) -> tuple[Interval, ...]:
    """Ranges for ==V.* and !=V.*.

    ==1.2.* -> [1.2.dev0, 1.3.dev0);  !=1.2.* -> complement.
    """
    lower = _base_dev0(base)
    upper = _next_prefix_dev0(base)
    if op == "==":
        return ((LowerBound(lower, True), UpperBound(upper, False)),)
    # !=
    return (
        (NEG_INF, UpperBound(lower, False)),
        (LowerBound(upper, True), POS_INF),
    )


def standard_ranges(op: str, version: Version, has_local: bool) -> tuple[Interval, ...]:
    """Ranges for the standard PEP 440 operators (no wildcard, no ===).

    *has_local* indicates whether the spec string included a ``+local``
    segment; relevant only for ``==`` / ``!=`` to decide whether the
    upper bound includes V's local family.
    """
    if op == ">=":
        return ((LowerBound(version, True), POS_INF),)

    if op == "<=":
        return (
            (
                NEG_INF,
                UpperBound(BoundaryVersion(version, BoundaryKind.AFTER_LOCALS), True),
            ),
        )

    if op == ">":
        if version.dev is not None:
            # >V.devN: dev versions have no post-releases, so the
            # next real version is V.dev(N+1).
            lower_bound = version.__replace__(dev=version.dev + 1, local=None)
            return ((LowerBound(lower_bound, True), POS_INF),)
        if version.post is not None:
            # >V.postN: next real version is V.post(N+1).dev0.
            lower_bound = version.__replace__(post=version.post + 1, dev=0, local=None)
            return ((LowerBound(lower_bound, True), POS_INF),)
        # >V (final or pre-release V): exclude V itself, V+local, and
        # every V.postN per PEP 440.
        return (
            (
                LowerBound(BoundaryVersion(version, BoundaryKind.AFTER_POSTS), False),
                POS_INF,
            ),
        )

    if op == "<":
        # <V excludes pre-releases of V when V is not a pre-release.
        # V.dev0 is the earliest pre-release of V.
        bound = (
            version if version.is_prerelease else version.__replace__(dev=0, local=None)
        )
        if bound <= MIN_VERSION:
            return ()
        return ((NEG_INF, UpperBound(bound, False)),)

    if op == "~=":
        prefix = version.__replace__(release=version.release[:-1])
        return (
            (LowerBound(version, True), UpperBound(_next_prefix_dev0(prefix), False)),
        )

    # ==1.4 includes every local version of 1.4, and !=1.4 excludes them all.
    upper = (
        version if has_local else BoundaryVersion(version, BoundaryKind.AFTER_LOCALS)
    )

    if op == "==":
        return ((LowerBound(version, True), UpperBound(upper, True)),)

    if op == "!=":
        return (
            (NEG_INF, UpperBound(version, False)),
            (LowerBound(upper, False), POS_INF),
        )

    raise ValueError(f"Unknown operator: {op!r}")  # pragma: no cover


def bounds_for_spec(
    op: str, version_str: str, version: Version
) -> tuple[Interval, ...]:
    """Ranges for one specifier's ``(op, version_str)``.

    Dispatches between the wildcard and standard builders. ``version`` is the
    parsed ``version_str`` (its base, without the trailing ``.*``, for
    wildcards). ``===`` is not handled here; its match is a literal string
    compared in :mod:`packaging.specifiers`.
    """
    if version_str.endswith(".*"):
        return wildcard_ranges(op, version)
    return standard_ranges(op, version, "+" in version_str)


def intersect_specifier_bounds(
    per_specifier_ranges: Iterator[tuple[Interval, ...]],
) -> SearchBounds:
    """Intersect the specifiers before building a search index for the set."""
    result: Sequence[Interval] = next(per_specifier_ranges)
    for sub in per_specifier_ranges:
        result = intersect_ranges(result, sub)
        if not result:
            break

    return index_intervals(result)


def matches_bounds_only(
    ranges: Sequence[Interval] | IntervalIndex, version: Version
) -> bool:
    """Whether ``version`` falls within any of ``ranges``.

    Ranges are sorted and non-overlapping. An indexed collection can reuse
    the same search for membership and filtering.
    """
    if isinstance(ranges, IntervalIndex):
        return ranges.contains(version)

    key = version._key_cache or version._key
    for lower, upper in ranges:
        if key < (lower._filter_key or lower.filter_key()):
            return False
        if key < (upper._filter_key or upper.filter_key()):
            return True
    return False


def resolve_prereleases(
    configured: bool | None, autodetected: bool | None
) -> bool | None:
    """Resolve a specifier's effective default pre-release policy.

    An explicit ``configured`` value wins; otherwise an autodetected ``True``
    propagates and anything else falls back to the PEP 440 default (``None``).
    """
    if configured is not None:
        return configured

    if autodetected:
        return True

    return None
