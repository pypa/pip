import os

from pip.utils import appdirs


def test_cache(script, monkeypatch):
    result = script.pip("cache", "location")
    lines = result.stdout.splitlines()
    assert len(lines) == 1

    for k, v in script.environ.items():
        monkeypatch.setenv(k, v)
    cache_dir = os.path.join(appdirs.user_cache_dir("pip"), "wheels")
    assert cache_dir in lines
