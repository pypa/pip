import ntpath
import os
import posixpath
import sys
from typing import Generator
from unittest import mock

import pytest
from pip._vendor import platformdirs

from pip._internal.utils import appdirs


@pytest.fixture()
def platformdirs_win32(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:

    # Monkeypatch platformdirs to pretend we're running on Windows

    with monkeypatch.context() as m:
        m.setattr(sys, "platform", "win32")
        m.setattr(os, "path", ntpath)
        platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()
        yield

    platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()


@pytest.fixture()
def platformdirs_darwin(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:

    # Monkeypatch platformdirs to pretend we're running on macOS

    with monkeypatch.context() as m:
        m.setattr(sys, "platform", "darwin")
        m.setattr(os, "path", posixpath)
        platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()
        yield

    platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()


@pytest.fixture()
def platformdirs_linux(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:

    # Monkeypatch platformdirs to pretend we're running on Linux

    with monkeypatch.context() as m:
        m.setattr(sys, "platform", "linux")
        m.setattr(os, "path", posixpath)
        platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()
        yield

    platformdirs.PlatformDirs = platformdirs._set_platform_dir_class()


class TestUserCacheDir:
    @pytest.mark.usefixtures("platformdirs_win32")
    def test_user_cache_dir_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _get_win_folder = mock.Mock(return_value="C:\\Users\\test\\AppData\\Local")

        monkeypatch.setattr(
            platformdirs.windows,  # type: ignore[attr-defined]
            "get_win_folder",
            _get_win_folder,
            raising=False,
        )

        assert (
            appdirs.user_cache_dir("pip")
            == "C:\\Users\\test\\AppData\\Local\\pip\\Cache"
        )
        assert _get_win_folder.call_args_list == [mock.call("CSIDL_LOCAL_APPDATA")]

    @pytest.mark.usefixtures("platformdirs_darwin")
    def test_user_cache_dir_osx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.user_cache_dir("pip") == "/home/test/Library/Caches/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_cache_dir_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.user_cache_dir("pip") == "/home/test/.cache/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_cache_dir_linux_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", "/home/test/.other-cache")
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.user_cache_dir("pip") == "/home/test/.other-cache/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_cache_dir_linux_home_slash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Verify that we are not affected by https://bugs.python.org/issue14768
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("HOME", "/")

        assert appdirs.user_cache_dir("pip") == "/.cache/pip"

    def test_user_cache_dir_unicode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        if sys.platform != "win32":
            return

        def my_get_win_folder(csidl_name):
            return "\u00DF\u00E4\u03B1\u20AC"

        monkeypatch.setattr(platformdirs.windows, "get_win_folder", my_get_win_folder)

        # Do not use the isinstance expression directly in the
        # assert statement, as the Unicode characters in the result
        # cause pytest to fail with an internal error on Python 2.7
        result_is_str = isinstance(appdirs.user_cache_dir("test"), str)
        assert result_is_str, "user_cache_dir did not return a str"

        # Test against regression #3463
        from pip._internal.cli.main_parser import create_main_parser

        create_main_parser().print_help()  # This should not crash


class TestSiteConfigDirs:
    @pytest.mark.usefixtures("platformdirs_win32")
    def test_site_config_dirs_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _get_win_folder = mock.Mock(return_value="C:\\ProgramData")

        monkeypatch.setattr(
            platformdirs.windows,  # type: ignore[attr-defined]
            "get_win_folder",
            _get_win_folder,
            raising=False,
        )

        assert appdirs.site_config_dirs("pip") == ["C:\\ProgramData\\pip"]
        assert _get_win_folder.call_args_list == [mock.call("CSIDL_COMMON_APPDATA")]

    @pytest.mark.usefixtures("platformdirs_darwin")
    def test_site_config_dirs_osx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.site_config_dirs("pip") == [
            "/Library/Preferences/pip",
            "/Library/Application Support/pip",
        ]

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_site_config_dirs_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)

        assert appdirs.site_config_dirs("pip") == ["/etc/xdg/pip", "/etc"]

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_site_config_dirs_linux_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "pathsep", ":")
        monkeypatch.setenv("XDG_CONFIG_DIRS", "/spam:/etc:/etc/xdg")

        assert appdirs.site_config_dirs("pip") == [
            "/spam/pip",
            "/etc/pip",
            "/etc/xdg/pip",
            "/etc",
        ]

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_site_config_dirs_linux_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "pathsep", ":")
        monkeypatch.setenv("XDG_CONFIG_DIRS", "")
        assert appdirs.site_config_dirs("pip") == ["/etc/xdg/pip", "/etc"]


class TestUserConfigDir:
    @pytest.mark.usefixtures("platformdirs_win32")
    def test_user_config_dir_win_no_roaming(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _get_win_folder = mock.Mock(return_value="C:\\Users\\test\\AppData\\Local")

        monkeypatch.setattr(
            platformdirs.windows,  # type: ignore[attr-defined]
            "get_win_folder",
            _get_win_folder,
            raising=False,
        )

        assert (
            appdirs.user_config_dir("pip", roaming=False)
            == "C:\\Users\\test\\AppData\\Local\\pip"
        )
        assert _get_win_folder.call_args_list == [mock.call("CSIDL_LOCAL_APPDATA")]

    @pytest.mark.usefixtures("platformdirs_win32")
    def test_user_config_dir_win_yes_roaming(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _get_win_folder = mock.Mock(return_value="C:\\Users\\test\\AppData\\Roaming")

        monkeypatch.setattr(
            platformdirs.windows,  # type: ignore[attr-defined]
            "get_win_folder",
            _get_win_folder,
            raising=False,
        )

        assert (
            appdirs.user_config_dir("pip") == "C:\\Users\\test\\AppData\\Roaming\\pip"
        )
        assert _get_win_folder.call_args_list == [mock.call("CSIDL_APPDATA")]

    @pytest.mark.usefixtures("platformdirs_darwin")
    def test_user_config_dir_osx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", "/home/test")

        if os.path.isdir("/home/test/Library/Application Support/"):
            assert (
                appdirs.user_config_dir("pip")
                == "/home/test/Library/Application Support/pip"
            )
        else:
            assert appdirs.user_config_dir("pip") == "/home/test/.config/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_config_dir_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.user_config_dir("pip") == "/home/test/.config/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_config_dir_linux_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.other-config")
        monkeypatch.setenv("HOME", "/home/test")

        assert appdirs.user_config_dir("pip") == "/home/test/.other-config/pip"

    @pytest.mark.usefixtures("platformdirs_linux")
    def test_user_config_dir_linux_home_slash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Verify that we are not affected by https://bugs.python.org/issue14768
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", "/")

        assert appdirs.user_config_dir("pip") == "/.config/pip"
