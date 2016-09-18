import os

import pytest

from pip.utils import appdirs


def test_wheel_cache_location(script, monkeypatch):
    result = script.pip("cache", "location")
    lines = result.stdout.splitlines()
    assert len(lines) == 1

    for k, v in script.environ.items():
        monkeypatch.setenv(k, v)
    cache_dir = os.path.join(appdirs.user_cache_dir("pip"), "wheels")
    assert cache_dir in lines


def test_cache_rejects_invalid_cache_type(script):
    result = script.pip("cache", "--type", "wombat", "location",
                        expect_error=True)
    assert "invalid choice" in result.stderr


@pytest.mark.parametrize("cache_type", ["all", "wheel", "http"])
def test_cache_info(script, cache_type):
    result = script.pip("cache", "-t", cache_type, "info")
    assert "Size:" in result.stdout
