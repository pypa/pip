from tests.lib import PipTestEnvironment, TestData


def test_index_strategy_first_match_functional(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Functional test for --index-strategy first-match.
    Index 1: data.index_url("simple") -> contains simple 1.0
    Index 2: data.index_url("yanked") -> contains simple 1.0, 2.0, 3.0

    Note: We use --no-build-isolation to avoid needing setuptools from
    the test indexes, since we're only testing index selection logic.
    """
    # Verify best-match (default) picks 2.0 (3.0 is yanked)
    result = script.pip(
        "install",
        "simple",
        "--dry-run",
        "--no-build-isolation",
        "--index-url",
        data.index_url("simple"),
        "--extra-index-url",
        data.index_url("yanked"),
    )
    assert "Would install simple-2.0" in result.stdout, (
        f"Actual output: {result.stdout}"
    )

    # Verify first-match picks 1.0 from the first index (index-url)
    result = script.pip(
        "install",
        "simple",
        "--dry-run",
        "--no-build-isolation",
        "--index-strategy",
        "first-match",
        "--index-url",
        data.index_url("simple"),
        "--extra-index-url",
        data.index_url("yanked"),
    )
    assert "Would install simple-1.0" in result.stdout, (
        f"Actual output: {result.stdout}"
    )


def test_index_strategy_find_links_combo(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Verify that find-links are still collected in first-match mode.
    Find-links: data.find_links -> contains 3.0
    Index-url: data.index_url("simple") -> contains 1.0
    Even in first-match mode, find-links should be searched first and 3.0 picked.

    Note: We use --no-build-isolation to avoid needing setuptools from
    the test indexes, since we're only testing index selection logic.
    """
    result = script.pip(
        "install",
        "simple",
        "--dry-run",
        "--no-build-isolation",
        "--index-strategy",
        "first-match",
        "--find-links",
        data.find_links,
        "--index-url",
        data.index_url("simple"),
    )
    assert "Would install simple-3.0" in result.stdout, (
        f"Actual output: {result.stdout}"
    )
