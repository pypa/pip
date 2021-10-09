import pytest


@pytest.mark.network
def test_timeout(script):
    result = script.pip(
        "--timeout",
        "0.0001",
        "install",
        "-vvv",
        "INITools",
        expect_error=True,
    )
    assert (
        "Could not fetch URL https://pypi.org/simple/initools/: "
        "connection error: HTTPSConnectionPool(host='pypi.org', port=443): "
        "Max retries exceeded with url: /simple/initools/ "
    ) in result.stdout
