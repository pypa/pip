from tests.lib import run_pip, reset_env


def test_timeout():
    reset_env()
    result = run_pip("--timeout", "0.01", "install", "-vvv", "INITools",
        expect_error=True,
    )
    assert "Could not fetch URL https://pypi.python.org/simple/INITools/: timed out" in result.stdout
    assert "Could not fetch URL https://pypi.python.org/simple/: timed out" in result.stdout
