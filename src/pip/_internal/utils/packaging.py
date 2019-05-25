from __future__ import absolute_import

import logging
from email.parser import FeedParser

from pip._vendor import pkg_resources
from pip._vendor.packaging import specifiers, version

from pip._internal.utils.misc import display_path
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Tuple
    from email.message import Message
    from pip._vendor.pkg_resources import Distribution


logger = logging.getLogger(__name__)


def check_requires_python(requires_python, version_info):
    # type: (Optional[str], Tuple[int, ...]) -> bool
    """
    Check if the given Python version matches a `requires_python` specifier.

    :param version_info: A 3-tuple of ints representing the Python
        major-minor-micro version to check (e.g. `sys.version_info[:3]`).

    Returns `True` if the version of python in use matches the requirement.
    Returns `False` if the version of python in use does not matches the
    requirement.

    Raises an InvalidSpecifier if `requires_python` have an invalid format.
    """
    if requires_python is None:
        # The package provides no information
        return True
    requires_python_specifier = specifiers.SpecifierSet(requires_python)

    python_version = version.parse('.'.join(map(str, version_info)))
    return python_version in requires_python_specifier


def get_metadata(dist):
    # type: (Distribution) -> Message
    if (isinstance(dist, pkg_resources.DistInfoDistribution) and
            dist.has_metadata('METADATA')):
        metadata = dist.get_metadata('METADATA')
    elif dist.has_metadata('PKG-INFO'):
        metadata = dist.get_metadata('PKG-INFO')
    else:
        logger.warning("No metadata found in %s", display_path(dist.location))
        metadata = ''

    feed_parser = FeedParser()
    feed_parser.feed(metadata)
    return feed_parser.close()


def get_requires_python(dist):
    # type: (pkg_resources.Distribution) -> Optional[str]
    """
    Return the "Requires-Python" metadata for a distribution, or None
    if not present.
    """
    pkg_info_dict = get_metadata(dist)
    requires_python = pkg_info_dict.get('Requires-Python')

    if requires_python is not None:
        # Convert to a str to satisfy the type checker, since requires_python
        # can be a Header object.
        requires_python = str(requires_python)

    return requires_python


def get_installer(dist):
    # type: (Distribution) -> str
    if dist.has_metadata('INSTALLER'):
        for line in dist.get_metadata_lines('INSTALLER'):
            if line.strip():
                return line.strip()
    return ''
