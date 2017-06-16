"""Helpers for caches
"""

import hashlib
import os.path


def get_cache_path_for_link(cache_dir, link):
    """
    Return a directory to store cached wheels in for link.

    Because there are M wheels for any one sdist, we provide a directory
    to cache them in, and then consult that directory when looking up
    cache hits.

    We only insert things into the cache if they have plausible version
    numbers, so that we don't contaminate the cache with things that were not
    unique. E.g. ./package might have dozens of installs done for it and build
    a version of 0.0...and if we built and cached a wheel, we'd end up using
    the same wheel even if the source has been edited.

    :param cache_dir: The cache_dir being used by pip.
    :param link: The link of the sdist for which this will cache wheels.
    """

    # We want to generate an url to use as our cache key, we don't want to just
    # re-use the URL because it might have other items in the fragment and we
    # don't care about those.
    key_parts = [link.url_without_fragment]
    if link.hash_name is not None and link.hash is not None:
        key_parts.append("=".join([link.hash_name, link.hash]))
    key_url = "#".join(key_parts)

    # Encode our key url with sha224, we'll use this because it has similar
    # security properties to sha256, but with a shorter total output (and thus
    # less secure). However the differences don't make a lot of difference for
    # our use case here.
    hashed = hashlib.sha224(key_url.encode()).hexdigest()

    # We want to nest the directories some to prevent having a ton of top level
    # directories where we might run out of sub directories on some FS.
    parts = [hashed[:2], hashed[2:4], hashed[4:6], hashed[6:]]

    # Inside of the base location for cached wheels, expand our parts and join
    # them all together.
    return os.path.join(cache_dir, "wheels", *parts)
