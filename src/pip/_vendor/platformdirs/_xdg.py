"""XDG environment variable mixin for Unix and macOS."""

from __future__ import annotations

import os
import posixpath
import sys
from contextlib import suppress
from pathlib import Path
from typing import Final

from .api import PlatformDirsABC


class XDGMixin(PlatformDirsABC):
    """Mixin that checks XDG environment variables, falling back to platform-specific defaults via ``super()``."""

    @property
    def user_data_dir(self) -> str:
        """Data directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default."""
        if path := _xdg_dir("XDG_DATA_HOME"):
            return self._append_app_name_and_version(path, private=True)
        return super().user_data_dir

    @property
    def _site_data_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_DATA_DIRS"):
            return [self._join_app_name_and_version(p) for p in xdg_dirs]
        return super()._site_data_dirs

    @property
    def site_data_dir(self) -> str:
        """Data directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default."""
        return self._select_site_dirs(self._site_data_dirs)

    @property
    def user_config_dir(self) -> str:
        """Config directory tied to the user, from ``$XDG_CONFIG_HOME`` if set, else platform default."""
        if path := _xdg_dir("XDG_CONFIG_HOME"):
            return self._append_app_name_and_version(path, private=True)
        return super().user_config_dir

    @property
    def _site_config_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_CONFIG_DIRS"):
            return [self._join_app_name_and_version(p) for p in xdg_dirs]
        return super()._site_config_dirs

    @property
    def site_config_dir(self) -> str:
        """Config directories shared by users, from ``$XDG_CONFIG_DIRS`` if set, else platform default."""
        return self._select_site_dirs(self._site_config_dirs)

    @property
    def user_cache_dir(self) -> str:
        """Cache directory tied to the user, from ``$XDG_CACHE_HOME`` if set, else platform default."""
        if path := _xdg_dir("XDG_CACHE_HOME"):
            return self._append_app_name_and_version(path, private=True)
        return super().user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """State directory tied to the user, from ``$XDG_STATE_HOME`` if set, else platform default."""
        if path := _xdg_dir("XDG_STATE_HOME"):
            return self._append_app_name_and_version(path, private=True)
        return super().user_state_dir

    @property
    def user_runtime_dir(self) -> str:
        """Runtime directory tied to the user, from ``$XDG_RUNTIME_DIR`` if set and private, else platform default."""
        from .unix import _runtime_dir_problem, _warn_once  # ruff:ignore[import-outside-top-level]  # unix imports _xdg

        if path := _xdg_dir("XDG_RUNTIME_DIR"):
            with suppress(OSError):
                self._optionally_create_directory(path, private=True)
            # Another user can pre-create the path in a shared parent, and XDG requires an owned runtime dir with mode 0700.
            if not (problem := _runtime_dir_problem(path, missing_ok=not self.ensure_exists)):
                return self._append_app_name_and_version(path, private=True)
            _warn_once(f"XDG_RUNTIME_DIR {problem}, falling back to the platform default")
        return super().user_runtime_dir

    @property
    def site_runtime_dir(self) -> str:
        """Runtime directory shared by users, from ``$XDG_RUNTIME_DIR`` if set, else platform default."""
        if path := _xdg_dir("XDG_RUNTIME_DIR"):
            return self._append_app_name_and_version(path, private=False)
        return super().site_runtime_dir

    @property
    def user_documents_dir(self) -> str:
        """Documents directory tied to the user, from ``$XDG_DOCUMENTS_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_DOCUMENTS_DIR") or super().user_documents_dir

    @property
    def user_downloads_dir(self) -> str:
        """Downloads directory tied to the user, from ``$XDG_DOWNLOAD_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_DOWNLOAD_DIR") or super().user_downloads_dir

    @property
    def user_pictures_dir(self) -> str:
        """Pictures directory tied to the user, from ``$XDG_PICTURES_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_PICTURES_DIR") or super().user_pictures_dir

    @property
    def user_videos_dir(self) -> str:
        """Videos directory tied to the user, from ``$XDG_VIDEOS_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_VIDEOS_DIR") or super().user_videos_dir

    @property
    def user_music_dir(self) -> str:
        """Music directory tied to the user, from ``$XDG_MUSIC_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_MUSIC_DIR") or super().user_music_dir

    @property
    def user_desktop_dir(self) -> str:
        """Desktop directory tied to the user, from ``$XDG_DESKTOP_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_DESKTOP_DIR") or super().user_desktop_dir

    @property
    def user_projects_dir(self) -> str:
        """Projects directory tied to the user, from ``$XDG_PROJECTS_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_PROJECTS_DIR") or super().user_projects_dir

    @property
    def user_publicshare_dir(self) -> str:
        """Public share directory tied to the user, from ``$XDG_PUBLICSHARE_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_PUBLICSHARE_DIR") or super().user_publicshare_dir

    @property
    def user_templates_dir(self) -> str:
        """Templates directory tied to the user, from ``$XDG_TEMPLATES_DIR`` if set, else platform default."""
        return self._xdg_media_dir("XDG_TEMPLATES_DIR") or super().user_templates_dir

    def _xdg_media_dir(self, env_var: str) -> str | None:
        if path := _xdg_dir(env_var):
            self._optionally_create_media_directory(path)
        return path

    @property
    def user_fonts_dir(self) -> str:
        """Fonts directory tied to the user, from ``$XDG_DATA_HOME/fonts`` if set, else platform default."""
        if path := _xdg_dir("XDG_DATA_HOME"):
            # posixpath keeps the XDG separator even when this mixin runs on a non-POSIX host.
            return posixpath.join(path, "fonts")
        return super().user_fonts_dir

    @property
    def user_applications_dir(self) -> str:
        """Applications directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default."""
        if path := _xdg_dir("XDG_DATA_HOME"):
            return os.path.join(os.path.expanduser(path), "applications")  # ruff:ignore[os-path-expanduser, os-path-join]
        return super().user_applications_dir

    @property
    def _site_applications_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_DATA_DIRS"):
            return [os.path.join(p, "applications") for p in xdg_dirs]  # ruff:ignore[os-path-join]
        return super()._site_applications_dirs

    @property
    def site_applications_dir(self) -> str:
        """Applications directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default."""
        dirs = self._site_applications_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]


def _xdg_dir(env_var: str) -> str | None:
    path: Final = os.environ.get(env_var, "")
    return path if posixpath.isabs(path) else None


def _xdg_dir_list(env_var: str) -> list[str]:
    return [path for path in os.environ.get(env_var, "").split(os.pathsep) if posixpath.isabs(path)]


def _expand_user(path: str) -> str:
    """Expand the leading ``~`` of ``path`` like :func:`os.path.expanduser`, treating a relative ``HOME`` as unset on POSIX.

    :raises RuntimeError: if the home directory cannot be resolved to an absolute path.

    """
    if sys.platform != "win32" and "HOME" in os.environ and not _is_absolute(os.environ["HOME"]):
        # expanduser uses HOME verbatim, so an empty one roots the path at / and a relative one at the working directory
        expanded = path
        with suppress(ImportError, KeyError):
            import pwd  # ruff:ignore[import-outside-top-level]  # missing on WASI

            expanded = pwd.getpwuid(os.getuid()).pw_dir.rstrip("/") + path[1:] or "/"
    else:
        expanded = os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]  # str(Path) rewrites separators on Windows
    if not _is_absolute(expanded):
        msg = f"could not determine the home directory for {path!r}, set an absolute HOME or XDG variable"
        raise RuntimeError(msg)
    return expanded


def _is_absolute(path: str) -> bool:
    # is_absolute accepts a Windows drive path, posixpath.isabs the POSIX home the Unix class gets on any host
    return posixpath.isabs(path) or Path(path).is_absolute()


__all__ = [
    "XDGMixin",
    "_expand_user",
    "_xdg_dir",
]
