import optparse

import pytest

from pip._internal.cli.autocompletion import get_path_completion_type


@pytest.mark.parametrize(
    "word, metavar",
    [
        ("-r", "file"),
        ("--requirement", "file"),
        ("--requirement=", "file"),
        ("-r", "dir"),
        ("-r", "path"),
        ("-r", "path/url"),
    ],
)
def test_path_completion_type(word: str, metavar: str) -> None:
    """Return the declared metavar, including combined alternatives such as path/url."""
    option = optparse.Option("-r", "--requirement", metavar=metavar)

    # The shell index includes the executable and the empty word being completed.
    assert get_path_completion_type(["install", word], 3, iter([option])) == metavar


@pytest.mark.parametrize(
    "word, metavar, help_text",
    [
        ("--other", "file", None),
        ("requirement", "file", None),
        ("-r", None, None),
        ("-r", "url", None),
        ("-r", "filename", None),
        ("-r", "file", optparse.SUPPRESS_HELP),
    ],
)
def test_no_path_completion_type(
    word: str, metavar: str | None, help_text: str | None
) -> None:
    """Only matching, visible options with a path metavar trigger path completion."""
    option = optparse.Option("-r", "--requirement", metavar=metavar, help=help_text)

    assert get_path_completion_type(["install", word], 3, [option]) is None


def test_path_completion_without_previous_word() -> None:
    """Completing immediately after pip must not index a nonexistent previous word."""
    option = optparse.Option("-r", metavar="file")

    assert get_path_completion_type([], 1, [option]) is None
