from tests.lib import TestData, make_test_finder


def test_index_strategy_best_match(data: TestData) -> None:
    """Test the default 'best-match' strategy searches all indexes."""
    finder = make_test_finder(
        index_urls=[data.index_url("simple"), data.find_links],
        index_strategy="best-match",
    )
    # data.index_url("simple") has simple 1.0
    # data.find_links has simple 3.0, 2.0, 1.0
    versions = finder.find_all_candidates("simple")

    # Best match should return versions from all indexes
    version_strs = [str(v.version) for v in versions]
    assert "1.0" in version_strs
    assert "3.0" in version_strs
    assert "2.0" in version_strs
    # In best-match, we expect everything to be collected.
    # Total 4 versions found across both indexes.
    assert len(version_strs) == 4


def test_index_strategy_first_match(data: TestData) -> None:
    """Test the 'first-match' strategy stops after the first index with hits."""
    # Order: Index 1 (v1.0) then Index 2 (v3.0, v2.0, v1.0)
    finder = make_test_finder(
        index_urls=[data.index_url("simple"), data.find_links],
        index_strategy="first-match",
    )

    versions = finder.find_all_candidates("simple")

    # Should stop after Index 1
    version_strs = [str(v.version) for v in versions]
    assert version_strs == ["1.0"]


def test_index_strategy_first_match_reversed(data: TestData) -> None:
    """Test first-match stops at the first index even if it contains better versions."""
    # Order: Index 1 (v3.0, v2.0, v1.0) then Index 2 (v1.0)
    finder = make_test_finder(
        index_urls=[data.find_links, data.index_url("simple")],
        index_strategy="first-match",
    )

    versions = finder.find_all_candidates("simple")

    # Should stop after Index 1 (find_links)
    version_strs = [str(v.version) for v in versions]
    assert version_strs == ["3.0", "2.0", "1.0"]
    assert "1.0" in version_strs
    # Should not have versions from Index 2 (even though 1.0 is duplicate)
    assert len(version_strs) == 3


def test_index_strategy_find_links_priority(data: TestData) -> None:
    """Test that find-links are always collected even in first-match mode."""
    finder = make_test_finder(
        find_links=[data.find_links],
        index_urls=[data.index_url("simple")],
        index_strategy="first-match",
    )

    versions = finder.find_all_candidates("simple")

    # Should collect find-links PLUS the first matching index
    version_strs = [str(v.version) for v in versions]
    # find_links (3.0, 2.0, 1.0) + index_url (1.0)
    assert version_strs == ["3.0", "2.0", "1.0", "1.0"]
