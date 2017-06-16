from pip.cache import WheelCache
from pip.compat import expanduser


class TestWheelCache:

    def test_expands_path(self):
        wc = WheelCache("~/.foo/", None)
        assert wc._cache_dir == expanduser("~/.foo/")

    def test_falsey_path_none(self):
        wc = WheelCache(False, None)
        assert wc._cache_dir is None
