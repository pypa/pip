"""Cache Management
"""

import os
import errno
import logging

from pip._vendor.packaging.utils import canonicalize_name

import pip.index
from pip.compat import expanduser
from pip.download import path_to_url
from pip.wheel import Wheel, InvalidWheelFilename
from pip.utils.cache import get_cache_path_for_link

logger = logging.getLogger(__name__)


class WheelCache(object):
    """A cache of wheels for future installs."""

    def __init__(self, cache_dir, format_control):
        """Create a wheel cache.

        :param cache_dir: The root of the cache.
        :param format_control: A pip.index.FormatControl object to limit
            binaries being read from the cache.
        """
        self._cache_dir = expanduser(cache_dir) if cache_dir else None
        self._format_control = format_control

    def cached_wheel(self, link, package_name):
        not_cached = (
            not self._cache_dir or
            not link or
            link.is_wheel or
            not link.is_artifact or
            not package_name
        )

        if not_cached:
            return link

        canonical_name = canonicalize_name(package_name)
        formats = pip.index.fmt_ctl_formats(
            self._format_control, canonical_name
        )
        if "binary" not in formats:
            return link
        root = get_cache_path_for_link(self._cache_dir, link)
        try:
            wheel_names = os.listdir(root)
        except OSError as err:
            if err.errno in {errno.ENOENT, errno.ENOTDIR}:
                return link
            raise
        candidates = []
        for wheel_name in wheel_names:
            try:
                wheel = Wheel(wheel_name)
            except InvalidWheelFilename:
                continue
            if not wheel.supported():
                # Built for a different python/arch/etc
                continue
            candidates.append((wheel.support_index_min(), wheel_name))
        if not candidates:
            return link
        candidates.sort()
        path = os.path.join(root, candidates[0][1])
        return pip.index.Link(path_to_url(path))
