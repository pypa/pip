from __future__ import absolute_import
import logging
import sys

from pip._vendor.packaging import specifiers
from pip._vendor.packaging import version

logger = logging.getLogger(__name__)


def check_requires_python(requires_python):
    """
    Check if the python version in use match the `requires_python` specifier.

    Returns `True` if the version of python in use matches the requirement.
    Returns `False` if the version of python in use does not matches the
    requirement.

    Raises an InvalidSpecifier if `requires_python` have an invalid format.
    """
    if requires_python is None:
        # The package provides no information
        return True
    requires_python_specifier = specifiers.SpecifierSet(requires_python)

    # We only use major.minor.micro
    python_version = version.parse('.'.join(map(str, sys.version_info[:3])))
    return python_version in requires_python_specifier
