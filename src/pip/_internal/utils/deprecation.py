"""
A module that implements tooling to enable easy warnings about deprecations.
"""
from __future__ import absolute_import

import logging
import warnings

from pip._vendor.packaging.version import parse

from pip import __version__ as current_version
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, Optional  # noqa: F401


class PipDeprecationWarning(Warning):
    pass


_original_showwarning = None  # type: Any


# Warnings <-> Logging Integration
def _showwarning(message, category, filename, lineno, file=None, line=None):
    if file is not None:
        if _original_showwarning is not None:
            _original_showwarning(
                message, category, filename, lineno, file, line,
            )
    elif issubclass(category, PipDeprecationWarning):
        # We use a specially named logger which will handle all of the
        # deprecation messages for pip.
        logger = logging.getLogger("pip._internal.deprecations")
        logger.warning(message)
    else:
        _original_showwarning(
            message, category, filename, lineno, file, line,
        )


def install_warning_logger():
    # Enable our Deprecation Warnings
    warnings.simplefilter("default", PipDeprecationWarning, append=True)

    global _original_showwarning

    if _original_showwarning is None:
        _original_showwarning = warnings.showwarning
        warnings.showwarning = _showwarning


def deprecated(reason, replacement, gone_in, issue=None):
    # type: (str, Optional[str], Optional[str], Optional[int]) -> None
    """Helper to deprecate existing functionality.
    """
    # NOTE: treat replacement, gone_in, issue as keyword only arguments.

    # Construct a nice message.
    # This is purposely eagerly formatted as we want it to appear as if someone
    # typed this entire message out.
    message = "DEPRECATION: " + reason
    if replacement is not None:
        message += " A possible replacement is {}.".format(replacement)
    if issue is not None:
        url = "https://github.com/pypa/pip/issues/" + str(issue)
        message += " You can find discussion regarding this at {}.".format(url)

    # Raise as an error if it has to be removed.
    if gone_in is not None and parse(current_version) >= parse(gone_in):
        raise PipDeprecationWarning(message)
    warnings.warn(message, category=PipDeprecationWarning, stacklevel=2)
