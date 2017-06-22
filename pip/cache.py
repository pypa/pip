"""Cache Management
"""

import errno
import logging
import os
import tempfile

from pip._vendor.packaging.utils import canonicalize_name

import pip.index
from pip.compat import expanduser
from pip.download import path_to_url
from pip.utils import rmtree
from pip.utils.cache import get_cache_path_for_link
from pip.wheel import InvalidWheelFilename, Wheel

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
        # Ephemeral cache: store wheels just for this run
        self._ephem_cache_dir = tempfile.mkdtemp(suffix='-pip-ephem-cache')
        self._format_control = format_control

    def cached_wheel(self, link, package_name):
        orig_link = link
        link = cached_wheel(
            self._cache_dir, link, self._format_control, package_name)
        if link is orig_link:
            link = cached_wheel(
                self._ephem_cache_dir, link, self._format_control,
                package_name)
        return link

    def cleanup(self):
        rmtree(self._ephem_cache_dir)


def cached_wheel(cache_dir, link, format_control, package_name):
    not_cached = (
        not cache_dir or
        not link or
        link.is_wheel or
        not link.is_artifact or
        not package_name
    )

    if not_cached:
        return link

    canonical_name = canonicalize_name(package_name)
    formats = pip.index.fmt_ctl_formats(
        format_control, canonical_name
    )
    if "binary" not in formats:
        return link
    root = get_cache_path_for_link(cache_dir, link)
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
