import os
from pathlib import Path

import pytest
from pip._vendor.packaging.tags import Tag, interpreter_name, interpreter_version

from pip._internal.cache import WheelCache, _contains_egg_info, _hash_dict
from pip._internal.models.link import Link
from pip._internal.utils.misc import ensure_dir


@pytest.mark.parametrize(
    "s, expected",
    [
        # Trivial.
        ("pip-18.0", True),
        # Ambiguous.
        ("foo-2-2", True),
        ("im-valid", True),
        # Invalid.
        ("invalid", False),
        ("im_invalid", False),
    ],
)
def test_contains_egg_info(s: str, expected: bool) -> None:
    result = _contains_egg_info(s)
    assert result == expected


def test_falsey_path_none() -> None:
    wc = WheelCache("")
    assert wc.cache_dir is None


def test_subdirectory_fragment() -> None:
    """
    Test the subdirectory URL fragment is part of the cache key.
    """
    wc = WheelCache("/tmp/.foo/")
    link1 = Link("git+https://g.c/o/r#subdirectory=d1")
    link2 = Link("git+https://g.c/o/r#subdirectory=d2")
    assert wc.get_path_for_link(link1) != wc.get_path_for_link(link2)


def test_wheel_name_filter(tmpdir: Path) -> None:
    """
    Test the wheel cache filters on wheel name when several wheels
    for different package are stored under the same cache directory.
    """
    wc = WheelCache(os.fspath(tmpdir))
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


def test_cache_hash() -> None:
    h = _hash_dict({"url": "https://g.c/o/r"})
    assert h == "72aa79d3315c181d2cc23239d7109a782de663b6f89982624d8c1e86"
    h = _hash_dict({"url": "https://g.c/o/r", "subdirectory": "sd"})
    assert h == "8b13391b6791bf7f3edeabb41ea4698d21bcbdbba7f9c7dc9339750d"
    h = _hash_dict({"subdirectory": "/\xe9e"})
    assert h == "f83b32dfa27a426dec08c21bf006065dd003d0aac78e7fc493d9014d"


def test_link_to_cache(tmpdir: Path) -> None:
    """
    Test that Link.from_json() produces Links with consistent cache
    locations
    """
    wc = WheelCache(os.fspath(tmpdir))
    # Define our expectations for stable cache path.
    i_name = interpreter_name()
    i_version = interpreter_version()
    key_parts = {
        "url": "https://files.pythonhosted.org/packages/a6/91/"
        "86a6eac449ddfae239e93ffc1918cf33fd9bab35c04d1e963b311e347a73/"
        "netifaces-0.11.0.tar.gz",
        "sha256": "043a79146eb2907edf439899f262b3dfe41717d34124298ed281139a8b93ca32",
        "interpreter_name": i_name,
        "interpreter_version": i_version,
    }
    expected_hash = _hash_dict(key_parts)
    parts = [
        expected_hash[:2],
        expected_hash[2:4],
        expected_hash[4:6],
        expected_hash[6:],
    ]
    pathed_hash = os.path.join(*parts)
    # Check working from a Link produces the same result.
    file_data = {
        "filename": "netifaces-0.11.0.tar.gz",
        "hashes": {
            "sha256": key_parts["sha256"],
        },
        "requires-python": "",
        "url": key_parts["url"],
        "yanked": False,
    }
    page_url = "https://pypi.org/simple/netifaces/"
    link = Link.from_json(file_data=file_data, page_url=page_url)
    assert link
    path = wc.get_path_for_link(link)
    assert pathed_hash in path


def test_get_cache_entry(tmpdir: Path) -> None:
    wc = WheelCache(os.fspath(tmpdir))
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
    entry = wc.get_cache_entry(persi_link, "persi", supported_tags)
    assert entry is not None
    assert entry.persistent

    entry = wc.get_cache_entry(ephem_link, "ephem", supported_tags)
    assert entry is not None
    assert not entry.persistent

    assert wc.get_cache_entry(other_link, "other", supported_tags) is None
