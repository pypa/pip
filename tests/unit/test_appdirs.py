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

    def test_site_config_dirs_win(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\ProgramData"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(sys, "platform", "win32")

        result = [
            e.replace("/", "\\")
            for e in appdirs.site_config_dirs("pip")
        ]
        assert result == ["C:\\ProgramData\\pip"]
        assert _get_win_folder.calls == [pretend.call("CSIDL_COMMON_APPDATA")]

    def test_site_config_dirs_osx(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert appdirs.site_config_dirs("pip") == \
            ["/Library/Application Support/pip"]

    def test_site_config_dirs_linux(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_DIRS")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.site_config_dirs("pip") == [
            '/etc/xdg/pip',
            '/etc'
        ]

    def test_site_config_dirs_linux_override(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_DIRS", "/spam:/etc:/etc/xdg")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.site_config_dirs("pip") == [
            '/spam/pip',
            '/etc/pip',
            '/etc/xdg/pip',
            '/etc'
        ]
