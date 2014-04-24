import sys

import pretend

from pip import appdirs


class TestUserCacheDir:

    def test_user_cache_dir_win(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Local"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(sys, "platform", "win32")

        assert (appdirs.user_cache_dir("pip").replace("/", "\\")
                == "C:\\Users\\test\\AppData\\Local\\pip\\Cache")
        assert _get_win_folder.calls == [pretend.call("CSIDL_LOCAL_APPDATA")]

    def test_user_cache_dir_osx(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert appdirs.user_cache_dir("pip") == "/home/test/Library/Caches/pip"

    def test_user_cache_dir_linux(self, monkeypatch):
        monkeypatch.delenv("XDG_CACHE_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_cache_dir("pip") == "/home/test/.cache/pip"

    def test_user_cache_dir_linux_override(self, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", "/home/test/.other-cache")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_cache_dir("pip") == "/home/test/.other-cache/pip"
