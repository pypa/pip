"""Cache Management
"""

import errno
import hashlib
import logging
import os

from pip._vendor.packaging.utils import canonicalize_name

import pip.index
from pip.compat import expanduser
from pip.download import path_to_url
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
        self._format_control = format_control

    def get_cache_path_for_link(self, link):
        """
        Return a directory to store cached wheels in for link.

        Because there are M wheels for any one sdist, we provide a directory
        to cache them in, and then consult that directory when looking up
        cache hits.

        We only insert things into the cache if they have plausible version
        numbers, so that we don't contaminate the cache with things that were
        not unique. E.g. ./package might have dozens of installs done for it
        and build a version of 0.0...and if we built and cached a wheel, we'd
        end up using the same wheel even if the source has been edited.

        :param link: The link of the sdist for which this will cache wheels.
        """

        # We want to generate an url to use as our cache key, we don't want to
        # just re-use the URL because it might have other items in the fragment
        # and we don't care about those.
        key_parts = [link.url_without_fragment]
        if link.hash_name is not None and link.hash is not None:
            key_parts.append("=".join([link.hash_name, link.hash]))
        key_url = "#".join(key_parts)

        # Encode our key url with sha224, we'll use this because it has similar
        # security properties to sha256, but with a shorter total output (and
        # thus less secure). However the differences don't make a lot of
        # difference for our use case here.
        hashed = hashlib.sha224(key_url.encode()).hexdigest()

        # We want to nest the directories some to prevent having a ton of top
        # level directories where we might run out of sub directories on some
        # FS.
        parts = [hashed[:2], hashed[2:4], hashed[4:6], hashed[6:]]

        # Inside of the base location for cached wheels, expand our parts and
        # join them all together.
        return os.path.join(self._cache_dir, "wheels", *parts)

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
        root = self.get_cache_path_for_link(link)
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
