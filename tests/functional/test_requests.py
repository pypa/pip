import pytest


@pytest.mark.skipif
def test_timeout(script):
    result = script.pip(
        "--timeout",
        "0.01",
        "install",
        "-vvv",
        "INITools",
        expect_error=True,
    )
    assert (
        "Could not fetch URL https://pypi.org/simple/INITools/: "
        "timed out" in result.stdout
    )
    assert "Could not fetch URL https://pypi.org/simple/: timed out" in result.stdout
