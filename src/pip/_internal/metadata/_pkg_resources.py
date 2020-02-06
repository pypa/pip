from __future__ import absolute_import

import logging
from email.parser import FeedParser

from pip._vendor import pkg_resources

from pip._internal.exceptions import NoneMetadataError
from pip._internal.utils.misc import display_path
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Iterator, Optional
    from email.message import Message
    from pip._vendor.pkg_resources import Distribution


logger = logging.getLogger(__name__)


def get_metadata(dist):
    # type: (Distribution) -> Message
    """
    :raises NoneMetadataError: if the distribution reports `has_metadata()`
        True but `get_metadata()` returns None.
    """
    metadata_name = 'METADATA'
    if (isinstance(dist, pkg_resources.DistInfoDistribution) and
            dist.has_metadata(metadata_name)):
        metadata = dist.get_metadata(metadata_name)
    elif dist.has_metadata('PKG-INFO'):
        metadata_name = 'PKG-INFO'
        metadata = dist.get_metadata(metadata_name)
    else:
        logger.warning("No metadata found in %s", display_path(dist.location))
        metadata = ''

    if metadata is None:
        raise NoneMetadataError(dist, metadata_name)

    feed_parser = FeedParser()
    # The following line errors out if with a "NoneType" TypeError if
    # passed metadata=None.
    feed_parser.feed(metadata)
    return feed_parser.close()


def get_file_lines(dist, name):
    # type: (Distribution, str) -> Optional[Iterator[str]]
    if not dist.has_metadata(name):
        return None
    return dist.get_metadata_lines(name)
