#######################################################################################
#
# Adapted from:
#  https://github.com/pypa/hatch/blob/5352e44/backend/src/hatchling/licenses/parse.py
#
# MIT License
#
# Copyright (c) 2017-present Ofek Lev <oss@ofek.dev>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# With additional allowance of arbitrary `LicenseRef-` identifiers, not just
# `LicenseRef-Public-Domain` and `LicenseRef-Proprietary`.
#
#######################################################################################
from __future__ import annotations

__lazy_modules__ = {f"{__spec__.parent}._spdx"}

import re
from typing import NewType, cast

from ._spdx import EXCEPTIONS, LICENSES

__all__ = [
    "InvalidLicenseExpression",
    "NormalizedLicenseExpression",
    "canonicalize_license_expression",
]


# Simple __dir__ implementation since there are no public submodules
def __dir__() -> list[str]:
    return __all__


license_ref_allowed = re.compile("^[A-Za-z0-9.-]+$")

# Match CPython's tokenizer limit for nested parentheses.
_MAX_PARENTHESIS_DEPTH = 200

NormalizedLicenseExpression = NewType("NormalizedLicenseExpression", str)
"""
A :class:`typing.NewType` of :class:`str`, representing a normalized
License-Expression.
"""


class InvalidLicenseExpression(ValueError):
    """Raised when a license-expression string is invalid

    >>> from packaging.licenses import canonicalize_license_expression
    >>> canonicalize_license_expression("invalid")
    Traceback (most recent call last):
        ...
    packaging.licenses.InvalidLicenseExpression: Unknown license: 'invalid'
    """


def _validate_expression_syntax(tokens: list[str], source: str) -> None:
    """
    Check token order and matching parentheses.

    Ignoring parentheses, names and operators follow this order::

        name -> AND/OR/WITH -> name -> ...

    An expression must end with a name or a closed group. Parentheses must
    be balanced. The caller checks the names and the rules for WITH.
    """
    parenthesis_depth = 0
    expect_operand = True

    for token in tokens:
        if token == "(":
            if not expect_operand or parenthesis_depth >= _MAX_PARENTHESIS_DEPTH:
                break
            parenthesis_depth += 1
        elif token == ")":
            if expect_operand or parenthesis_depth == 0:
                break
            parenthesis_depth -= 1
        elif token in {"or", "and", "with"}:
            if expect_operand:
                break
            expect_operand = True
        else:
            if not expect_operand:
                break
            expect_operand = False
    else:
        # All tokens were read: require a final name or group and no open parentheses.
        if not expect_operand and parenthesis_depth == 0:
            return

    message = f"Invalid license expression: {source!r}"
    raise InvalidLicenseExpression(message)


def canonicalize_license_expression(
    raw_license_expression: str,
) -> NormalizedLicenseExpression:
    """
    This function takes a valid License-Expression, and returns the normalized
    form of it.

    The return type is typed as :class:`NormalizedLicenseExpression`. This
    allows type checkers to help require that a string has passed through this
    function before use.

    :param str raw_license_expression: The License-Expression to canonicalize.
    :raises InvalidLicenseExpression: If the License-Expression is invalid due to an
        invalid/unknown license identifier or invalid syntax.

    .. doctest::

        >>> from packaging.licenses import canonicalize_license_expression
        >>> canonicalize_license_expression("mit")
        'MIT'
        >>> canonicalize_license_expression("mit and (apache-2.0 or bsd-2-clause)")
        'MIT AND (Apache-2.0 OR BSD-2-Clause)'
        >>> canonicalize_license_expression("(mit")
        Traceback (most recent call last):
          ...
        InvalidLicenseExpression: Invalid license expression: '(mit'
        >>> canonicalize_license_expression("Use-it-after-midnight")
        Traceback (most recent call last):
          ...
        InvalidLicenseExpression: Unknown license: 'Use-it-after-midnight'
    """
    if not raw_license_expression:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message)

    # Pad any parentheses so tokenization can be achieved by merely splitting on
    # whitespace.
    license_expression = raw_license_expression.replace("(", " ( ").replace(")", " ) ")
    licenseref_prefix = "LicenseRef-"

    # The idstring of a LicenseRef- is case-insensitive in SPDX, so all case
    # variants of one ref use the spelling of the first occurrence.
    license_refs: dict[str, str] = {}
    tokens = []
    for ref in license_expression.split():
        normalized = ref.lower()
        tokens.append(normalized)
        if normalized.startswith("licenseref-"):
            if not ref.isascii():
                message = f"Invalid licenseref (non-ASCII): {ref!r}"
                raise InvalidLicenseExpression(message)
            license_refs.setdefault(
                normalized, licenseref_prefix + ref[len(licenseref_prefix) :]
            )

    _validate_expression_syntax(tokens, raw_license_expression)

    # Take a final pass to check for unknown licenses/exceptions.
    normalized_tokens = []
    last_license_start = False
    for index, token in enumerate(tokens):
        if token in {"or", "and", "with", "(", ")"}:
            if token == "with" and (
                not last_license_start
                or index + 1 == len(tokens)
                or tokens[index + 1] in {"or", "and", "with", "(", ")"}
            ):
                message = f"Invalid license expression: {raw_license_expression!r}"
                raise InvalidLicenseExpression(message)
            normalized_tokens.append(token.upper())
            last_license_start = False
            continue

        if normalized_tokens and normalized_tokens[-1] == "WITH":
            if token not in EXCEPTIONS:
                message = f"Unknown license exception: {token!r}"
                raise InvalidLicenseExpression(message)

            normalized_tokens.append(EXCEPTIONS[token]["id"])
            last_license_start = False
        else:
            if token.endswith("+"):
                final_token = token[:-1]
                suffix = "+"
            else:
                final_token = token
                suffix = ""

            if final_token.startswith("licenseref-"):
                license_ref_id = final_token[len("licenseref-") :]
                if suffix or not license_ref_allowed.match(license_ref_id):
                    message = f"Invalid licenseref: {token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(license_refs[final_token])
            else:
                if final_token not in LICENSES:
                    message = f"Unknown license: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(LICENSES[final_token]["id"] + suffix)
            last_license_start = True

    normalized_expression = " ".join(normalized_tokens)

    return cast(
        "NormalizedLicenseExpression",
        normalized_expression.replace("( ", "(").replace(" )", ")"),
    )
