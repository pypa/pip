import sys

import pretend
import pytest

colorama = pytest.importorskip("pip._vendor.colorama")


@pytest.fixture
def SetConsoleTextAttribute(monkeypatch):
    """Monkey-patch the SetConsoleTextAttribute function.

    This fixture records calls to the win32 function via colorama's win32
    module. On non-Windows systems, this function is an empty stub. Note that
    colorama.win32 is an internal interface, and may change without notice.
    """
    from pip._vendor.colorama import win32

    wrapper = pretend.call_recorder(win32.SetConsoleTextAttribute)
    monkeypatch.setattr(win32, "SetConsoleTextAttribute", wrapper)

    return wrapper


def test_color_always(script, SetConsoleTextAttribute):
    """It uses colored output when passed --color=always."""
    ret = script.pip(
        "uninstall", "--color=always", "foo", allow_stderr_warning=True
    )

    if sys.platform == "win32":
        assert colorama.Fore.YELLOW not in ret.stderr
        assert SetConsoleTextAttribute.calls
    else:
        assert colorama.Fore.YELLOW in ret.stderr


def test_color_auto(script, SetConsoleTextAttribute):
    """It does not use colored output when passed --color=auto.

    Don't expect color because ``script`` redirects output to a pipe.
    """
    ret = script.pip(
        "uninstall", "--color=auto", "foo", allow_stderr_warning=True
    )
    assert colorama.Fore.YELLOW not in ret.stderr
    if sys.platform == "win32":
        assert not SetConsoleTextAttribute.calls


def test_color_never(script, SetConsoleTextAttribute):
    """It does not use colored output when passed --color=never."""
    ret = script.pip(
        "uninstall", "--color=never", "foo", allow_stderr_warning=True
    )
    assert colorama.Fore.YELLOW not in ret.stderr
    if sys.platform == "win32":
        assert not SetConsoleTextAttribute.calls
