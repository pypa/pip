from pip._internal.cache import WheelCache
from pip._internal.compat import expanduser


class TestWheelCache:

    def test_expands_path(self):
        wc = WheelCache("~/.foo/", None)
        assert wc.cache_dir == expanduser("~/.foo/")

    def test_falsey_path_none(self):
        wc = WheelCache(False, None)
        assert wc.cache_dir is None
