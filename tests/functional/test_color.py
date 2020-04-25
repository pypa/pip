import pytest

colorama = pytest.importorskip("pip._vendor.colorama")


def test_color_always(script):
    """It uses colored output when passed --color=always."""
    ret = script.pip(
        "uninstall", "--color=always", "foo", allow_stderr_warning=True
    )
    assert colorama.Fore.YELLOW in ret.stderr, "Expected color in output"


def test_color_auto(script):
    """It does not use colored output when passed --color=auto.

    Don't expect color because ``script`` redirects output to a pipe.
    """
    ret = script.pip(
        "uninstall", "--color=auto", "foo", allow_stderr_warning=True
    )
    assert colorama.Fore.YELLOW not in ret.stderr, "Expected no color in output"


def test_color_never(script):
    """It does not use colored output when passed --color=never."""
    ret = script.pip(
        "uninstall", "--color=never", "foo", allow_stderr_warning=True
    )
    assert colorama.Fore.YELLOW not in ret.stderr, "Expected no color in output"
