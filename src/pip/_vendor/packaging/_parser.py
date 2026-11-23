"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

__lazy_modules__ = {
    "ast",
    f"{__spec__.parent}._tokenizer",
    f"{__spec__.parent}.specifiers",
}

import ast
from typing import Literal, NamedTuple, TypeAlias, cast

from ._tokenizer import DEFAULT_RULES, ParserSyntaxError, Tokenizer
from .specifiers import InvalidSpecifier, SpecifierSet


class Node:
    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.value!r})>"

    def serialize(self) -> str:
        raise NotImplementedError

    def __getstate__(self) -> str:
        # Return just the value string for compactness and stability.
        return self.value

    def _restore_value(self, value: object) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"Cannot restore {self.__class__.__name__} value from {value!r}"
            )
        self.value = value

    def __setstate__(self, state: object) -> None:
        if isinstance(state, str):
            # New format (26.2+): just the value string.
            self._restore_value(state)
            return
        if isinstance(state, tuple) and len(state) == 2:
            # Old format (packaging <= 26.0, __slots__): (None, {slot: value}).
            _, slot_dict = state
            if isinstance(slot_dict, dict) and "value" in slot_dict:
                self._restore_value(slot_dict["value"])
                return
        if isinstance(state, dict) and "value" in state:
            # Old format (packaging <= 25.0, no __slots__): plain __dict__.
            self._restore_value(state["value"])
            return
        raise TypeError(f"Cannot restore {self.__class__.__name__} from {state!r}")


class Variable(Node):
    __slots__ = ()

    def serialize(self) -> str:
        return str(self)


class Value(Node):
    __slots__ = ()

    def serialize(self) -> str:
        value = str(self)
        if '"' not in value:
            return f'"{value}"'
        if "'" not in value:
            return f"'{value}'"
        raise ValueError(
            "Cannot serialize marker value containing both quote characters"
        )


class Op(Node):
    __slots__ = ()

    def serialize(self) -> str:
        return str(self)


MarkerLogical = Literal["and", "or"]
MarkerVar = Variable | Value
MarkerItem = tuple[MarkerVar, Op, MarkerVar]
MarkerAtom: TypeAlias = "MarkerItem | MarkerList"
MarkerList: TypeAlias = "list[MarkerAtom | MarkerLogical]"


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: list[str]
    specifier: str | SpecifierSet
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str | SpecifierSet, MarkerList | None]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier: str | SpecifierSet = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=url_start,
            expected="semicolon (after URL and whitespace)",
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        if tokenizer.rules is not DEFAULT_RULES:
            tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            expected=(
                "comma (within version specifier), semicolon (after version specifier)"
                if specifier
                else "semicolon (after name with no version specifier)"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, expected: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected {expected} or end",
            span_start=span_start,
            span_end=None,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    if tokenizer.rules is not DEFAULT_RULES:
        tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET"):
        # The default whitespace rule leaves no whitespace after the name.
        if tokenizer.rules is not DEFAULT_RULES:
            tokenizer.consume("WS")
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    tokenizer.consume("WS")
    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str | SpecifierSet:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    if not tokenizer.check("LEFT_PARENTHESIS"):
        # The caller already consumed the leading whitespace.
        if tokenizer.rules is not DEFAULT_RULES:
            return _parse_padded_version_many(tokenizer)
        return _parse_version_many(tokenizer)

    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        parsed_specifiers = _parse_padded_version_many(tokenizer)

    if tokenizer.rules is DEFAULT_RULES:
        tokenizer.consume("WS")
    return parsed_specifiers


def _parse_padded_version_many(tokenizer: Tokenizer) -> str | SpecifierSet:
    """
    padded_version_many = WS? version_many WS?
    """
    tokenizer.consume("WS")
    parsed_specifiers = _parse_version_many(tokenizer)
    # With the default rules, version_many consumes its trailing whitespace.
    if tokenizer.rules is not DEFAULT_RULES:
        tokenizer.consume("WS")
    return parsed_specifiers


def _try_parse_specifier_set(tokenizer: Tokenizer) -> SpecifierSet | None:
    """Parse the specifier list with :class:`SpecifierSet` in one pass.

    Returns ``None`` without consuming input if the text is not a valid
    ``version_many``; the token loop then parses it or reports the error.
    """
    token = tokenizer.peek("SPECIFIER_LIST")
    if token is None or not token.text:
        return None

    try:
        specifiers = SpecifierSet(token.text)
    except InvalidSpecifier:
        return None

    # SpecifierSet skips empty items, but the grammar only allows a trailing comma.
    commas = token.text.count(",")
    if len(specifiers) != commas + 1 and not (
        specifiers
        and len(specifiers) == commas
        and token.text.rstrip(" \t").endswith(",")
    ):
        return None

    tokenizer.consume_token(token)
    return specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str | SpecifierSet:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    if tokenizer.position == len(tokenizer.source):
        return ""
    specifier_set = _try_parse_specifier_set(tokenizer)
    if specifier_set is not None:
        return specifier_set

    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        specifier = tokenizer.read().text
        parsed_specifiers += specifier
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            message = ".* suffix can only be used with `==` or `!=` operators"
            if specifier.startswith("!=") or (
                specifier.startswith("==") and not specifier.startswith("===")
            ):
                message = (
                    ".* suffix cannot be used with pre-release, post-release, "
                    "dev or local versions"
                )
            tokenizer.raise_syntax_error(
                message,
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
# Parenthesized groups recurse, so cap their depth to report deeply nested input as
# a syntax error instead of exhausting the interpreter's recursion limit. The limit
# matches CPython's own parser, which allows 200 nested parentheses.
_MAX_MARKER_NESTING = 200


def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer, depth: int = 0) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression: MarkerList = [_parse_marker_atom(tokenizer, depth)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer, depth)
        expression.extend((cast("MarkerLogical", token.text), expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer, depth: int) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS"):
        if depth >= _MAX_MARKER_NESTING:
            tokenizer.raise_syntax_error(
                f"Marker expression is nested more than {_MAX_MARKER_NESTING} "
                "levels deep"
            )
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            if tokenizer.rules is not DEFAULT_RULES:
                tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer, depth + 1)
            if tokenizer.rules is not DEFAULT_RULES:
                tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    # Custom rules may consume only part of a whitespace run.
    if tokenizer.rules is not DEFAULT_RULES:
        tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    if tokenizer.rules is not DEFAULT_RULES:
        tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:  # noqa: RET503
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    position = tokenizer.position
    match = tokenizer.match_pattern(tokenizer.rules["VARIABLE"])
    if match is not None:
        return _process_marker_var(match[0])
    match = tokenizer.match_pattern(tokenizer.rules["QUOTED_STRING"])
    if match is not None:
        return _process_marker_value(tokenizer, match[0], position)
    tokenizer.raise_syntax_error(message="Expected a marker variable or quoted string")


def _process_marker_var(text: str) -> Variable:
    return process_env_var(text.replace(".", "_"))


def _process_marker_value(tokenizer: Tokenizer, text: str, position: int) -> Value:
    try:
        return process_python_str(text)
    except (SyntaxError, ValueError) as exc:
        raise ParserSyntaxError(
            "Invalid quoted string",
            source=tokenizer.source,
            span=(position, position + len(text)),
        ) from exc


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    # The tokenizer guarantees matching delimiters with no embedded delimiter.
    if "\\" not in python_str and python_str.isprintable():
        return Value(python_str[1:-1])

    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    rules = tokenizer.rules
    if tokenizer.match_pattern(rules["IN"]) is not None:
        return Op("in")
    elif tokenizer.match_pattern(rules["NOT"]) is not None:
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    match = tokenizer.match_pattern(rules["OP"])
    if match is not None:
        return Op(match[0])
    return tokenizer.raise_syntax_error(
        "Expected marker operator, one of <=, <, !=, ==, >=, >, ~=, ===, in, not in"
    )
