"""
This code wraps the vendored appdirs module to so the return values are
compatible for the current pip code base.

The intention is to rewrite current usages gradually, keeping the tests pass,
and eventually drop this after all usages are changed.
"""

import os
import sys

from pip._vendor import platformdirs as _appdirs


def user_cache_dir(appname: str) -> str:
    return _appdirs.user_cache_dir(appname, appauthor=False)


def _macos_user_config_dir(appname: str, roaming: bool = True) -> str:
    # Use ~/Application Support/pip, if the directory exists.
    path = _appdirs.user_data_dir(appname, appauthor=False, roaming=roaming)
    if os.path.isdir(path):
        return path

    # Use a Linux-like ~/.config/pip, by default.
    linux_like_path = "~/.config/"
    if appname:
        linux_like_path = os.path.join(linux_like_path, appname)

    return os.path.expanduser(linux_like_path)


def user_config_dir(appname: str, roaming: bool = True) -> str:
    if sys.platform == "darwin":
        return _macos_user_config_dir(appname, roaming)

    return _appdirs.user_config_dir(appname, appauthor=False, roaming=roaming)


# for the discussion regarding site_config_dir locations
# see <https://github.com/pypa/pip/issues/1733>
def site_config_dirs(appname: str) -> list[str]:
    if sys.platform == "darwin":
        dirval = _appdirs.site_data_dir(appname, appauthor=False, multipath=True)
        return dirval.split(os.pathsep)

    if sys.platform == "win32":
        try:
            # Causes FileNotFoundError on attempt to access a registry key that does
            # not exist. This should not break apart pip configuration loading.
            dirval = _appdirs.site_config_dir(appname, appauthor=False, multipath=True)
            return [dirval]
        except FileNotFoundError:
            return []

    # Unix-y system. Look in /etc as well.
    dirval = _appdirs.site_config_dir(appname, appauthor=False, multipath=True)
    return dirval.split(os.pathsep) + ["/etc"]
