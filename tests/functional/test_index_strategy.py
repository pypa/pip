from tests.lib import PipTestEnvironment, TestData


def test_index_strategy_first_match_functional(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Functional test for --index-strategy first-match.
    We set up two indexes:
    - Index A: simple 1.0
    - Index B: simple 2.0
    By default, pip should pick 2.0.
    With --index-strategy first-match and Index A first, it should pick 1.0.
    """
    # Create Index A
    index_a = script.scratch_path / "index_a"
    index_a.mkdir()
    pkg_a = index_a / "simple"
    pkg_a.mkdir()
    (pkg_a / "simple-1.0.tar.gz").touch()

    # Create Index B
    index_b = script.scratch_path / "index_b"
    index_b.mkdir()
    pkg_b = index_b / "simple"
    pkg_b.mkdir()
    (pkg_b / "simple-2.0.tar.gz").touch()

    # Verify best-match (default) picks 2.0
    result = script.pip(
        "install", "simple",
        "--dry-run",
        "--index-url", f"file:///{index_a.as_posix()}",
        "--extra-index-url", f"file:///{index_b.as_posix()}",
    )
    assert "Would install simple-2.0" in result.stdout

    # Verify first-match picks 1.0
    result = script.pip(
        "install", "simple",
        "--dry-run",
        "--index-strategy", "first-match",
        "--index-url", f"file:///{index_a.as_posix()}",
        "--extra-index-url", f"file:///{index_b.as_posix()}",
    )
    assert "Would install simple-1.0" in result.stdout

def test_index_strategy_find_links_combo(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Verify that find-links are still collected in first-match mode.
    """
    index_a = script.scratch_path / "index_a"
    index_a.mkdir()
    pkg_a = index_a / "simple"
    pkg_a.mkdir()
    (pkg_a / "simple-1.0.tar.gz").touch()

    find_links = script.scratch_path / "links"
    find_links.mkdir()
    (find_links / "simple-3.0.tar.gz").touch()

    # Should find 3.0 from find-links even if index_a is searched
    result = script.pip(
        "install", "simple",
        "--dry-run",
        "--index-strategy", "first-match",
        "--find-links", f"file:///{find_links.as_posix()}",
        "--index-url", f"file:///{index_a.as_posix()}",
    )
    assert "Would install simple-3.0" in result.stdout
