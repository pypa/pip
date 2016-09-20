import os
import re

import pytest

from pip.utils import appdirs


def test_cache_rejects_invalid_cache_type(script):
    result = script.pip("cache", "--type", "wombat", "info",
                        expect_error=True)
    assert "invalid choice" in result.stderr


@pytest.mark.parametrize("cache_type", ["all", "wheel", "http"])
def test_cache_info(script, monkeypatch, cache_type):
    result = script.pip("cache", "-t", cache_type, "info")

    for k, v in script.environ.items():
        monkeypatch.setenv(k, v)
    cache_base = appdirs.user_cache_dir("pip")
    wheel_cache_dir = os.path.join(cache_base, "wheels")
    http_cache_dir = os.path.join(cache_base, "http")

    assert "Size:" in result.stdout
    if cache_type == "wheel":
        assert "Location: %s" % wheel_cache_dir in result.stdout
        assert http_cache_dir not in result.stdout
    elif cache_type == "http":
        assert "Location: %s" % http_cache_dir in result.stdout
        assert wheel_cache_dir not in result.stdout
    else:
        assert "Location: %s" % wheel_cache_dir in result.stdout
        assert "Location: %s" % http_cache_dir in result.stdout


def test_cache_list(script, monkeypatch):
    for k, v in script.environ.items():
        monkeypatch.setenv(k, v)
    cache_base = appdirs.user_cache_dir("pip")
    wheel_cache_dir = os.path.join(cache_base, "wheels")
    destination = os.path.join(wheel_cache_dir, "arbitrary", "pathname")
    os.makedirs(destination)
    with open(os.path.join(destination, "zzz.whl"), "w"):
        pass
    result = script.pip("cache", "list")
    assert "zzz.whl" in result.stdout


def test_cache_rm(script, monkeypatch):
    for k, v in script.environ.items():
        monkeypatch.setenv(k, v)
    cache_base = appdirs.user_cache_dir("pip")
    wheel_cache_dir = os.path.join(cache_base, "wheels")
    os.makedirs(wheel_cache_dir)
    with open(os.path.join(wheel_cache_dir, "zzz.whl"), "w"):
        pass

    script.pip("cache", "rm", expect_error=True)
    result = script.pip("cache", "rm", "zzz.whl")
    assert re.match(r"^Removed.*zzz\.whl$", result.stdout)
