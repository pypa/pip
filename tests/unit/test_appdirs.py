import ntpath
import os
import posixpath
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
        monkeypatch.setattr(os, "path", ntpath)

        assert (appdirs.user_cache_dir("pip") ==
                "C:\\Users\\test\\AppData\\Local\\pip\\Cache")
        assert _get_win_folder.calls == [pretend.call("CSIDL_LOCAL_APPDATA")]

    def test_user_cache_dir_osx(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert appdirs.user_cache_dir("pip") == "/home/test/Library/Caches/pip"

    def test_user_cache_dir_linux(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.delenv("XDG_CACHE_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_cache_dir("pip") == "/home/test/.cache/pip"

    def test_user_cache_dir_linux_override(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("XDG_CACHE_HOME", "/home/test/.other-cache")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_cache_dir("pip") == "/home/test/.other-cache/pip"

    def test_user_cache_dir_linux_home_slash(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        # Verify that we are not affected by http://bugs.python.org/issue14768
        monkeypatch.delenv("XDG_CACHE_HOME")
        monkeypatch.setenv("HOME", "/")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_cache_dir("pip") == "/.cache/pip"

    def test_user_cache_dir_unicode(self, monkeypatch):
        if sys.platform != 'win32':
            return

        def my_get_win_folder(csidl_name):
            return u"\u00DF\u00E4\u03B1\u20AC"

        monkeypatch.setattr(appdirs, "_get_win_folder", my_get_win_folder)

        # Do not use the isinstance expression directly in the
        # assert statement, as the Unicode characters in the result
        # cause pytest to fail with an internal error on Python 2.7
        result_is_str = isinstance(appdirs.user_cache_dir('test'), str)
        assert result_is_str, "user_cache_dir did not return a str"

        # Test against regression #3463
        from pip import create_main_parser
        create_main_parser().print_help()  # This should not crash


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
        monkeypatch.setattr(os, "path", ntpath)

        assert appdirs.site_config_dirs("pip") == ["C:\\ProgramData\\pip"]
        assert _get_win_folder.calls == [pretend.call("CSIDL_COMMON_APPDATA")]

    def test_site_config_dirs_osx(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert appdirs.site_config_dirs("pip") == \
            ["/Library/Application Support/pip"]

    def test_site_config_dirs_linux(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.delenv("XDG_CONFIG_DIRS")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.site_config_dirs("pip") == [
            '/etc/xdg/pip',
            '/etc'
        ]

    def test_site_config_dirs_linux_override(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setattr(os, "pathsep", ':')
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
        monkeypatch.setattr(os, "path", ntpath)

        assert (appdirs.user_data_dir("pip") ==
                "C:\\Users\\test\\AppData\\Local\\pip")
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
        monkeypatch.setattr(os, "path", ntpath)

        assert (
            appdirs.user_data_dir("pip", roaming=True) ==
            "C:\\Users\\test\\AppData\\Roaming\\pip"
        )
        assert _get_win_folder.calls == [pretend.call("CSIDL_APPDATA")]

    def test_user_data_dir_osx(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert (appdirs.user_data_dir("pip") ==
                "/home/test/Library/Application Support/pip")

    def test_user_data_dir_linux(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.delenv("XDG_DATA_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_data_dir("pip") == "/home/test/.local/share/pip"

    def test_user_data_dir_linux_override(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("XDG_DATA_HOME", "/home/test/.other-share")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_data_dir("pip") == "/home/test/.other-share/pip"

    def test_user_data_dir_linux_home_slash(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        # Verify that we are not affected by http://bugs.python.org/issue14768
        monkeypatch.delenv("XDG_DATA_HOME")
        monkeypatch.setenv("HOME", "/")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_data_dir("pip") == "/.local/share/pip"


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
        monkeypatch.setattr(os, "path", ntpath)

        assert (
            appdirs.user_config_dir("pip", roaming=False) ==
            "C:\\Users\\test\\AppData\\Local\\pip"
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
        monkeypatch.setattr(os, "path", ntpath)

        assert (appdirs.user_config_dir("pip") ==
                "C:\\Users\\test\\AppData\\Roaming\\pip")
        assert _get_win_folder.calls == [pretend.call("CSIDL_APPDATA")]

    def test_user_config_dir_osx(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "darwin")

        assert (appdirs.user_config_dir("pip") ==
                "/home/test/Library/Application Support/pip")

    def test_user_config_dir_linux(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_config_dir("pip") == "/home/test/.config/pip"

    def test_user_config_dir_linux_override(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.other-config")
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_config_dir("pip") == "/home/test/.other-config/pip"

    def test_user_config_dir_linux_home_slash(self, monkeypatch):
        monkeypatch.setattr(appdirs, "WINDOWS", False)
        monkeypatch.setattr(os, "path", posixpath)
        # Verify that we are not affected by http://bugs.python.org/issue14768
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.setenv("HOME", "/")
        monkeypatch.setattr(sys, "platform", "linux2")

        assert appdirs.user_config_dir("pip") == "/.config/pip"
