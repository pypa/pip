import os

from pip._vendor.packaging.tags import Tag

from pip._internal.cache import WheelCache, _hash_dict
from pip._internal.models.format_control import FormatControl
from pip._internal.models.link import Link
from pip._internal.utils.misc import ensure_dir


def test_falsey_path_none():
    wc = WheelCache(False, None)
    assert wc.cache_dir is None


def test_subdirectory_fragment():
    """
    Test the subdirectory URL fragment is part of the cache key.
    """
    wc = WheelCache("/tmp/.foo/", None)
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
    cached_link = wc.get(link, "package", [Tag("py3", "none", "any")])
    assert cached_link is not link
    assert os.path.exists(cached_link.file_path)
    # package2 does not match wheel name
    assert wc.get(link, "package2", [Tag("py3", "none", "any")]) is link


def test_cache_hash():
    h = _hash_dict({"url": "https://g.c/o/r"})
    assert h == "72aa79d3315c181d2cc23239d7109a782de663b6f89982624d8c1e86"
    h = _hash_dict({"url": "https://g.c/o/r", "subdirectory": "sd"})
    assert h == "8b13391b6791bf7f3edeabb41ea4698d21bcbdbba7f9c7dc9339750d"
    h = _hash_dict({"subdirectory": "/\xe9e"})
    assert h == "f83b32dfa27a426dec08c21bf006065dd003d0aac78e7fc493d9014d"


def test_get_cache_entry(tmpdir):
    wc = WheelCache(tmpdir, FormatControl())
    persi_link = Link("https://g.c/o/r/persi")
    persi_path = wc.get_path_for_link(persi_link)
    ensure_dir(persi_path)
    with open(os.path.join(persi_path, "persi-1.0.0-py3-none-any.whl"), "w"):
        pass
    ephem_link = Link("https://g.c/o/r/ephem")
    ephem_path = wc.get_ephem_path_for_link(ephem_link)
    ensure_dir(ephem_path)
    with open(os.path.join(ephem_path, "ephem-1.0.0-py3-none-any.whl"), "w"):
        pass
    other_link = Link("https://g.c/o/r/other")
    supported_tags = [Tag("py3", "none", "any")]
    assert wc.get_cache_entry(persi_link, "persi", supported_tags).persistent
    assert not wc.get_cache_entry(ephem_link, "ephem", supported_tags).persistent
    assert wc.get_cache_entry(other_link, "other", supported_tags) is None
