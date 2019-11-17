import os

from pip._internal.cache import WheelCache, _hash_dict
from pip._internal.models.format_control import FormatControl
from pip._internal.models.link import Link
from pip._internal.utils.compat import expanduser
from pip._internal.utils.misc import ensure_dir


def test_expands_path():
    wc = WheelCache("~/.foo/", None)
    assert wc.cache_dir == expanduser("~/.foo/")


def test_falsey_path_none():
    wc = WheelCache(False, None)
    assert wc.cache_dir is None


def test_subdirectory_fragment():
    """
    Test the subdirectory URL fragment is part of the cache key.
    """
    wc = WheelCache("~/.foo/", None)
    link1 = Link("git+https://g.c/o/r#subdirectory=d1")
    link2 = Link("git+https://g.c/o/r#subdirectory=d2")
    assert wc.get_path_for_link(link1) != wc.get_path_for_link(link2)


def test_wheel_name_filter(tmpdir):
    """
    Test the wheel cache filters on wheel name when several wheels
    for different package are stored under the same cache directory.
    """
    wc = WheelCache(tmpdir, FormatControl())
    link = Link("https://g.c/package.tar.gz")
    cache_path = wc.get_path_for_link(link)
    ensure_dir(cache_path)
    with open(os.path.join(cache_path, "package-1.0-py3-none-any.whl"), "w"):
        pass
    # package matches wheel name
    assert wc.get(link, "package", [("py3", "none", "any")]) is not link
    # package2 does not match wheel name
    assert wc.get(link, "package2", [("py3", "none", "any")]) is link


def test_cache_hash():
    h = _hash_dict({"url": "https://g.c/o/r"})
    assert h == "c7d60d08b1079254d236e983501fa26c016d58d16010725b27ed0af2"
    h = _hash_dict({"url": "https://g.c/o/r", "subdirectory": "sd"})
    assert h == "9cba35d4ccf04b7cde751b44db347fd0f21fa47d1276e32f9d47864c"


def test_get_path_for_link_legacy(tmpdir):
    """
    Test that an existing cache entry that was created with the legacy hashing
    mechanism is used.
    """
    wc = WheelCache(tmpdir, FormatControl())
    link = Link("https://g.c/o/r")
    path = wc.get_path_for_link(link)
    legacy_path = wc.get_path_for_link_legacy(link)
    assert path != legacy_path
    ensure_dir(path)
    with open(os.path.join(path, "test-pyz-none-any.whl"), "w"):
        pass
    ensure_dir(legacy_path)
    with open(os.path.join(legacy_path, "test-pyx-none-any.whl"), "w"):
        pass
    expected_candidates = {"test-pyx-none-any.whl", "test-pyz-none-any.whl"}
    assert set(wc._get_candidates(link, "test")) == expected_candidates
