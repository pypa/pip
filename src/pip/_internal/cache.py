"""Cache Management
"""

import abc
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from pip._vendor.packaging.tags import Tag, interpreter_name, interpreter_version
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InvalidWheelFilename
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import vcs

logger = logging.getLogger(__name__)

_egg_info_re = re.compile(r"([a-z0-9_.]+)-([a-z0-9_.!+-]+)", re.IGNORECASE)

ORIGIN_JSON_NAME = "origin.json"


def _contains_egg_info(s: str) -> bool:
    """Determine whether the string looks like an egg_info.

    :param s: The string to parse. E.g. foo-2.1
    """
    return bool(_egg_info_re.search(s))


def should_cache(
    req: InstallRequirement,
) -> bool:
    """
    Return whether a built InstallRequirement can be stored in the persistent
    wheel cache, assuming the wheel cache is available, and _should_build()
    has determined a wheel needs to be built.
    """
    if not req.link:
        return False

    if req.link.is_wheel:
        return False

    if req.editable or not req.source_dir:
        # never cache editable requirements
        return False

    if req.link and req.link.is_vcs:
        # VCS checkout. Do not cache
        # unless it points to an immutable commit hash.
        assert not req.editable
        assert req.source_dir
        vcs_backend = vcs.get_backend_for_scheme(req.link.scheme)
        assert vcs_backend
        if vcs_backend.is_immutable_rev_checkout(req.link.url, req.source_dir):
            return True
        return False

    assert req.link
    base, ext = req.link.splitext()
    if _contains_egg_info(base):
        return True

    # Otherwise, do not cache.
    return False


def _hash_dict(d: Dict[str, str]) -> str:
    """Return a stable sha224 of a dictionary."""
    s = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha224(s.encode("ascii")).hexdigest()


class Cache(abc.ABC):
    """An abstract class - provides cache directories for data from links

    :param cache_dir: The root of the cache.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__()
        assert not cache_dir or os.path.isabs(cache_dir)
        self.cache_dir = cache_dir or None

    def _get_cache_path_parts(self, link: Link) -> List[str]:
        """Get parts of part that must be os.path.joined with cache_dir"""

        # We want to generate an url to use as our cache key, we don't want to
        # just re-use the URL because it might have other items in the fragment
        # and we don't care about those.
        key_parts = {"url": link.url_without_fragment}
        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash
        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        # Include interpreter name, major and minor version in cache key
        # to cope with ill-behaved sdists that build a different wheel
        # depending on the python version their setup.py is being run on,
        # and don't encode the difference in compatibility tags.
        # https://github.com/pypa/pip/issues/7296
        key_parts["interpreter_name"] = interpreter_name()
        key_parts["interpreter_version"] = interpreter_version()

        # Encode our key url with sha224, we'll use this because it has similar
        # security properties to sha256, but with a shorter total output (and
        # thus less secure). However the differences don't make a lot of
        # difference for our use case here.
        hashed = _hash_dict(key_parts)

        # We want to nest the directories some to prevent having a ton of top
        # level directories where we might run out of sub directories on some
        # FS.
        parts = [hashed[:2], hashed[2:4], hashed[4:6], hashed[6:]]

        return parts

    @abc.abstractmethod
    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached items in for link."""
        ...

    def cache_path(self, link: Link) -> Path:
        return Path(self.get_path_for_link(link))


class LinkMetadataCache(Cache):
    """Persistently store the metadata of dists found at each link."""

    def get_path_for_link(self, link: Link) -> str:
        parts = self._get_cache_path_parts(link)
        assert self.cache_dir
        return os.path.join(self.cache_dir, "link-metadata", *parts)


class WheelCacheBase(Cache):
    """Specializations to the cache concept for wheels."""

    @abc.abstractmethod
    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        """Returns a link to a cached item if it exists, otherwise returns the
        passed link.
        """
        ...

    def _can_cache(self, link: Link, canonical_package_name: str) -> bool:
        return bool(self.cache_dir and canonical_package_name and link)

    def _get_candidates(
        self, link: Link, canonical_package_name: str
    ) -> Iterator[Tuple[str, str]]:
        if not self._can_cache(link, canonical_package_name):
            return

        path = self.get_path_for_link(link)
        if not os.path.isdir(path):
            return

        for candidate in os.scandir(path):
            if candidate.is_file():
                yield (candidate.name, path)


class SimpleWheelCache(WheelCacheBase):
    """A cache of wheels for future installs."""

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)

    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached wheels for link

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
        parts = self._get_cache_path_parts(link)
        assert self.cache_dir
        # Store wheels within the root cache_dir
        return os.path.join(self.cache_dir, "wheels", *parts)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        candidates: List[Tuple[int, str, str]] = []

        if not package_name:
            return link

        canonical_package_name = canonicalize_name(package_name)
        for wheel_name, wheel_dir in self._get_candidates(link, canonical_package_name):
            try:
                wheel = Wheel(wheel_name)
            except InvalidWheelFilename:
                continue
            if canonicalize_name(wheel.name) != canonical_package_name:
                logger.debug(
                    "Ignoring cached wheel %s for %s as it "
                    "does not match the expected distribution name %s.",
                    wheel_name,
                    link,
                    package_name,
                )
                continue
            if not wheel.supported(supported_tags):
                # Built for a different python/arch/etc
                continue
            candidates.append(
                (
                    wheel.support_index_min(supported_tags),
                    wheel_name,
                    wheel_dir,
                )
            )

        if not candidates:
            return link

        _, wheel_name, wheel_dir = min(candidates)
        return Link(path_to_url(os.path.join(wheel_dir, wheel_name)))


class EphemWheelCache(SimpleWheelCache):
    """A SimpleWheelCache that creates it's own temporary cache directory"""

    def __init__(self) -> None:
        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.EPHEM_WHEEL_CACHE,
            globally_managed=True,
        )

        super().__init__(self._temp_dir.path)


class CacheEntry:
    def __init__(
        self,
        link: Link,
        persistent: bool,
    ):
        self.link = link
        self.persistent = persistent
        self.origin: Optional[DirectUrl] = None
        origin_direct_url_path = Path(self.link.file_path).parent / ORIGIN_JSON_NAME
        if origin_direct_url_path.exists():
            try:
                self.origin = DirectUrl.from_json(
                    origin_direct_url_path.read_text(encoding="utf-8")
                )
            except Exception as e:
                logger.warning(
                    "Ignoring invalid cache entry origin file %s for %s (%s)",
                    origin_direct_url_path,
                    link.filename,
                    e,
                )


class WheelCache(WheelCacheBase):
    """Wraps EphemWheelCache and SimpleWheelCache into a single Cache

    This Cache allows for gracefully degradation, using the ephem wheel cache
    when a certain link is not found in the simple wheel cache first.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)
        self._wheel_cache = SimpleWheelCache(cache_dir)
        self._ephem_cache = EphemWheelCache()

    def get_path_for_link(self, link: Link) -> str:
        return self._wheel_cache.get_path_for_link(link)

    def get_ephem_path_for_link(self, link: Link) -> str:
        return self._ephem_cache.get_path_for_link(link)

    def resolve_cache_dir(self, req: InstallRequirement) -> str:
        """Return the persistent or temporary cache directory where the built or
        downloaded wheel should be stored."""
        cache_available = bool(self.cache_dir)
        assert req.link, req
        if cache_available and should_cache(req):
            return self.get_path_for_link(req.link)
        return self.get_ephem_path_for_link(req.link)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        cache_entry = self.get_cache_entry(link, package_name, supported_tags)
        if cache_entry is None:
            return link
        return cache_entry.link

    def get_cache_entry(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Optional[CacheEntry]:
        """Returns a CacheEntry with a link to a cached item if it exists or
        None. The cache entry indicates if the item was found in the persistent
        or ephemeral cache.
        """
        retval = self._wheel_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=True)

        retval = self._ephem_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=False)

        return None

    @staticmethod
    def record_download_origin(cache_dir: str, download_info: DirectUrl) -> None:
        origin_path = Path(cache_dir) / ORIGIN_JSON_NAME
        if origin_path.exists():
            try:
                origin = DirectUrl.from_json(origin_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(
                    "Could not read origin file %s in cache entry (%s). "
                    "Will attempt to overwrite it.",
                    origin_path,
                    e,
                )
            else:
                # TODO: use DirectUrl.equivalent when
                # https://github.com/pypa/pip/pull/10564 is merged.
                if origin.url != download_info.url:
                    logger.warning(
                        "Origin URL %s in cache entry %s does not match download URL "
                        "%s. This is likely a pip bug or a cache corruption issue. "
                        "Will overwrite it with the new value.",
                        origin.url,
                        cache_dir,
                        download_info.url,
                    )
        origin_path.write_text(download_info.to_json(), encoding="utf-8")
