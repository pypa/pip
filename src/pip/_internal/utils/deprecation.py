"""
A module that implements tooling to enable easy warnings about deprecations.
"""

import logging
import warnings
from typing import Any, Optional, TextIO, Type, Union

from pip._vendor.packaging.version import parse

from pip import __version__ as current_version  # NOTE: tests patch this name.

DEPRECATION_MSG_PREFIX = "DEPRECATION: "
DEPRECATION_MESSAGE = DEPRECATION_MSG_PREFIX + "{reason}"
GONE_IN_MESSAGE_FUTURE = "pip {gone_in} will enforce this behavior change."
GONE_IN_MESSAGE_PAST = "This behavior change has been enforced since pip {gone_in}."
REPLACEMENT_MESSAGE = "A possible replacement is {replacement}."
FEATURE_FLAG_MESSAGE = (
    "You can temporarily use the flag --use-feature={feature_flag} "
    "to test the upcoming behavior."
)
ISSUE_MESSAGE = "Discussion can be found at https://github.com/pypa/pip/issues/{issue}."


class PipDeprecationWarning(Warning):
    pass


_original_showwarning: Any = None


# Warnings <-> Logging Integration
def _showwarning(
    message: Union[Warning, str],
    category: Type[Warning],
    filename: str,
    lineno: int,
    file: Optional[TextIO] = None,
    line: Optional[str] = None,
) -> None:
    if file is not None:
        if _original_showwarning is not None:
            _original_showwarning(message, category, filename, lineno, file, line)
    elif issubclass(category, PipDeprecationWarning):
        # We use a specially named logger which will handle all of the
        # deprecation messages for pip.
        logger = logging.getLogger("pip._internal.deprecations")
        logger.warning(message)
    else:
        _original_showwarning(message, category, filename, lineno, file, line)


def install_warning_logger() -> None:
    # Enable our Deprecation Warnings
    warnings.simplefilter("default", PipDeprecationWarning, append=True)

    global _original_showwarning

    if _original_showwarning is None:
        _original_showwarning = warnings.showwarning
        warnings.showwarning = _showwarning


def deprecated(
    *,
    reason: str,
    replacement: Optional[str],
    gone_in: Optional[str],
    feature_flag: Optional[str] = None,
    issue: Optional[int] = None,
) -> None:
    """Helper to deprecate existing functionality.

    reason:
        Textual reason shown to the user about why this functionality has
        been deprecated. Should be a complete sentence.
    replacement:
        Textual suggestion shown to the user about what alternative
        functionality they can use.
    gone_in:
        The version of pip does this functionality should get removed in.
        Raises an error if pip's current version is greater than or equal to
        this.
    feature_flag:
        Command-line flag of the form --use-feature={feature_flag} for testing
        upcoming functionality.
    issue:
        Issue number on the tracker that would serve as a useful place for
        users to find related discussion and provide feedback.
    """

    # Determine whether or not the feature is already gone in this version.
    is_gone = gone_in is not None and parse(current_version) >= parse(gone_in)
    # Allow variable substitutions within the "reason" variable.
    formatted_reason = reason.format(gone_in=gone_in)
    # Construct a nice message.
    #   This is eagerly formatted as we want it to get logged as if someone
    #   typed this entire message out.
    formatted_deprecation_message = DEPRECATION_MESSAGE.format(reason=formatted_reason)
    gone_in_message = GONE_IN_MESSAGE_PAST if is_gone else GONE_IN_MESSAGE_FUTURE
    formatted_gone_in_message = (
        gone_in_message.format(gone_in=gone_in) if gone_in else None
    )
    formatted_replacement_message = (
        REPLACEMENT_MESSAGE.format(replacement=replacement) if replacement else None
    )
    formatted_feature_flag_message = (
        None
        if is_gone or not feature_flag
        else FEATURE_FLAG_MESSAGE.format(feature_flag=feature_flag)
    )
    formatted_issue_message = ISSUE_MESSAGE.format(issue=issue) if issue else None
    sentences = [
        formatted_deprecation_message,
        formatted_gone_in_message,
        formatted_replacement_message,
        formatted_feature_flag_message,
        formatted_issue_message,
    ]
    message = " ".join(sentence for sentence in sentences if sentence)

    # Raise as an error if this behaviour is no longer supported.
    if is_gone:
        raise PipDeprecationWarning(message)
    else:
        warnings.warn(message, category=PipDeprecationWarning, stacklevel=2)
