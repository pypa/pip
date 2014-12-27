import sys

import pretend

from pip.utils import appdirs


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
        monkeypatch.setattr(appdirs, "WINDOWS", True)

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


class TestSiteConfigDirs:

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
        monkeypatch.setattr(appdirs, "WINDOWS", True)

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


class TestUserDataDir:

    def test_user_data_dir_win_no_roaming(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Local"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(appdirs, "WINDOWS", True)

        assert (appdirs.user_data_dir("pip").replace("/", "\\")
                == "C:\\Users\\test\\AppData\\Local\\pip")
        assert _get_win_folder.calls == [pretend.call("CSIDL_LOCAL_APPDATA")]

    def test_user_data_dir_win_yes_roaming(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Roaming"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(appdirs, "WINDOWS", True)

        assert (appdirs.user_data_dir("pip", roaming=True).replace("/", "\\")
                == "C:\\Users\\test\\AppData\\Roaming\\pip")
        assert _get_win_folder.calls == [pretend.call("CSIDL_APPDATA")]

    def test_user_data_dir_osx(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert (appdirs.user_data_dir("pip")
                == "/home/test/Library/Application Support/pip")

    def test_user_data_dir_linux(self, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_data_dir("pip") == "/home/test/.local/share/pip"

    def test_user_data_dir_linux_override(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "/home/test/.other-share")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_data_dir("pip") == "/home/test/.other-share/pip"


class TestUserConfigDir:

    def test_user_config_dir_win_no_roaming(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Local"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(appdirs, "WINDOWS", True)

        assert (
            appdirs.user_config_dir("pip", roaming=False).replace("/", "\\")
            == "C:\\Users\\test\\AppData\\Local\\pip"
        )
        assert _get_win_folder.calls == [pretend.call("CSIDL_LOCAL_APPDATA")]

    def test_user_config_dir_win_yes_roaming(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Roaming"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(appdirs, "WINDOWS", True)

        assert (appdirs.user_config_dir("pip").replace("/", "\\")
                == "C:\\Users\\test\\AppData\\Roaming\\pip")
        assert _get_win_folder.calls == [pretend.call("CSIDL_APPDATA")]

    def test_user_config_dir_osx(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert (appdirs.user_config_dir("pip")
                == "/home/test/Library/Application Support/pip")

    def test_user_config_dir_linux(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_config_dir("pip") == "/home/test/.config/pip"

    def test_user_config_dir_linux_override(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.other-config")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_config_dir("pip") == "/home/test/.other-config/pip"


class TestUserLogDir:

    def test_user_log_dir_win(self, monkeypatch):
        @pretend.call_recorder
        def _get_win_folder(base):
            return "C:\\Users\\test\\AppData\\Local"

        monkeypatch.setattr(
            appdirs,
            "_get_win_folder",
            _get_win_folder,
            raising=False,
        )
        monkeypatch.setattr(appdirs, "WINDOWS", True)

        assert (appdirs.user_log_dir("pip").replace("/", "\\")
                == "C:\\Users\\test\\AppData\\Local\\pip\\Logs")
        assert _get_win_folder.calls == [pretend.call("CSIDL_LOCAL_APPDATA")]

    def test_user_log_dir_osx(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert (appdirs.user_log_dir("pip")
                == "/home/test/Library/Logs/pip")

    def test_uuser_log_dir_linux(self, monkeypatch):
        monkeypatch.delenv("XDG_CACHE_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_log_dir("pip") == "/home/test/.cache/pip/log"

    def test_user_log_dir_linux_override(self, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", "/home/test/.other-cache")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_log_dir("pip") == "/home/test/.other-cache/pip/log"
