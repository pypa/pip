# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import absolute_import, division, print_function

import operator
import os
import platform
import sys

from ._compat import string_types
from ._parsing import (
    ParseException, ParseResults, Optional, Literal as L, ZeroOrMore, Group,
    Forward, QuotedString, stringStart, stringEnd,
)
from .specifiers import Specifier, InvalidSpecifier


__all__ = [
    "InvalidMarker", "UndefinedComparison", "Marker", "default_environment",
]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP XX.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class Node(object):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<{0}({1!r})>".format(self.__class__.__name__, str(self))


class Variable(Node):
    pass


class Value(Node):
    pass


VARIABLE = (
    L("implementation_version") |
    L("python_implementation") |
    L("implementation_name") |
    L("python_full_version") |
    L("platform_release") |
    L("platform_version") |
    L("platform_machine") |
    L("platform_system") |
    L("python_version") |
    L("sys_platform") |
    L("os_name") |
    L("extra")  # TODO: How are we going to handle extra?
)
VARIABLE.setParseAction(lambda s, l, t: Variable(t[0]))

VERSION_CMP = (
    L("===") |
    L("==") |
    L(">=") |
    L("<=") |
    L("!=") |
    L("~=") |
    L(">") |
    L("<")
)

MARKER_OP = VERSION_CMP | L("not in") | L("in")

MARKER_VALUE = QuotedString("'") | QuotedString('"')
MARKER_VALUE.setParseAction(lambda s, l, t: Value(t[0]))

BOOLOP = L("and") | L("or")

MARKER_VAR = VARIABLE | MARKER_VALUE

MARKER_ITEM = Group(MARKER_VAR + MARKER_OP + MARKER_VAR)
MARKER_ITEM.setParseAction(lambda s, l, t: tuple(t[0]))

LPAREN = L("(").suppress()
RPAREN = L(")").suppress()

MARKER_EXPR = Forward()
MARKER_ATOM = MARKER_ITEM | Group(LPAREN + MARKER_EXPR + RPAREN)
MARKER_EXPR << MARKER_ATOM + ZeroOrMore(BOOLOP + MARKER_EXPR)

MARKER = stringStart + Optional(MARKER_EXPR) + stringEnd


def _coerce_parse_result(results):
    if isinstance(results, ParseResults):
        return [_coerce_parse_result(i) for i in results]
    else:
        return results


def _format_marker(marker, first=True):
    assert isinstance(marker, (list, tuple, string_types))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (isinstance(marker, list) and len(marker) == 1
            and isinstance(marker[0], (list, tuple))):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return '{0} {1} "{2}"'.format(*marker)
    else:
        return marker


_operators = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs, op, rhs):
    try:
        spec = Specifier("".join([op, rhs]))
    except InvalidSpecifier:
        pass
    else:
        return spec.contains(lhs)

    oper = _operators.get(op)
    if oper is None:
        raise UndefinedComparison(
            "Undefined {0!r} on {1!r} and {2!r}.".format(op, lhs, rhs)
        )

    return oper(lhs, rhs)


def _evaluate_markers(markers, environment):
    groups = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, string_types))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker
            if isinstance(lhs, Variable):
                value = _eval_op(environment[lhs.value], op, rhs.value)
            else:
                value = _eval_op(lhs.value, op, environment[rhs.value])
            groups[-1].append(value)
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def default_environment():
    iver = "{0.major}.{0.minor}.{0.micro}".format(sys.implementation.version)
    if sys.implementation.version.releaselevel != "final":
        iver = "{0}{1[0]}{2}".format(
            iver,
            sys.implementation.version.releaselevel,
            sys.implementation.version.serial,
        )

    return {
        "implementation_name": sys.implementation.name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version()[:3],
        "sys_platform": sys.platform,
    }


class Marker(object):

    def __init__(self, marker=""):
        try:
            self._markers = _coerce_parse_result(MARKER.parseString(marker))
        except ParseException:
            self._markers = None

        # We do this because we can't do raise ... from None in Python 2.x
        if self._markers is None:
            raise InvalidMarker("Invalid marker: {0!r}".format(marker))

    def __str__(self):
        return _format_marker(self._markers)

    def __repr__(self):
        return "<Marker({0!r})>".format(str(self))

    def __bool__(self):
        return bool(self._markers)

    def __nonzero__(self):
        return self.__bool__()

    def evaluate(self, environment=None):
        current_environment = default_environment()
        if environment is not None:
            current_environment.update(environment)

        return _evaluate_markers(self._markers, current_environment)
