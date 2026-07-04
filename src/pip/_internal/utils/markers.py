from __future__ import annotations

from collections.abc import Iterable

from pip._vendor.packaging._parser import MarkerList, Op, Value, Variable
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.utils import canonicalize_name


def _eval_extra_marker(
    lhs: Variable | Value,
    op: Op,
    rhs: Variable | Value,
    extras: frozenset[str],
) -> bool | None:
    lhs_is_extra = isinstance(lhs, Variable) and lhs.value == "extra"
    rhs_is_extra = isinstance(rhs, Variable) and rhs.value == "extra"
    if not lhs_is_extra and not rhs_is_extra:
        return None

    if lhs_is_extra and isinstance(rhs, Value):
        extra = rhs.value
    elif rhs_is_extra and isinstance(lhs, Value):
        extra = lhs.value
    else:
        return False

    normalized_extra = canonicalize_name(extra)
    extras_to_evaluate = extras or frozenset({""})
    if op.value == "==":
        return any(extra == normalized_extra for extra in extras_to_evaluate)
    if op.value == "!=":
        return all(extra != normalized_extra for extra in extras_to_evaluate)
    if op.value == "in":
        return any(
            Marker._from_markers([(lhs, op, rhs)]).evaluate({"extra": extra})
            for extra in extras_to_evaluate
        )
    if op.value == "not in":
        return all(
            Marker._from_markers([(lhs, op, rhs)]).evaluate({"extra": extra})
            for extra in extras_to_evaluate
        )
    return False


def _evaluate_markers(markers: MarkerList, extras: frozenset[str]) -> bool:
    # Keep the boolean marker walk aligned with packaging's evaluator; only
    # ``extra`` comparisons need set-wide handling here.
    groups: list[list[bool]] = [[]]

    for marker in markers:
        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, extras))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker
            extra_result = _eval_extra_marker(lhs, op, rhs, extras)
            if extra_result is not None:
                groups[-1].append(extra_result)
                continue

            groups[-1].append(Marker._from_markers([marker]).evaluate())
        elif marker == "or":
            groups.append([])
        elif marker == "and":
            pass
        else:  # pragma: no cover
            raise TypeError(f"Unexpected marker {marker!r}")

    return any(all(item) for item in groups)


def match_markers(
    marker: Marker,
    extras_requested: Iterable[str] | None = None,
) -> bool:
    """Evaluate a marker using the selected extras set for this requirement."""
    extras = frozenset(canonicalize_name(extra) for extra in extras_requested or ())
    return _evaluate_markers(marker._markers, extras)
