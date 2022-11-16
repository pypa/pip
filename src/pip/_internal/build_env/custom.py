import os
import site
import sys
import textwrap
from collections import OrderedDict
from typing import TYPE_CHECKING, Collection, Iterable, List, Set

from pip._vendor.certifi import where

from pip._internal.cli.spinners import open_spinner
from pip._internal.locations import get_platlib, get_purelib
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

from .base import OverlayBuildEnvironment, Prefix, get_runnable_pip, iter_install_flags

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


def _get_system_sitepackages() -> Set[str]:
    """Get system site packages

    Usually from site.getsitepackages,
    but fallback on `get_purelib()/get_platlib()` if unavailable
    (e.g. in a virtualenv created by virtualenv<20)

    Returns normalized set of strings.
    """
    if hasattr(site, "getsitepackages"):
        system_sites = site.getsitepackages()
    else:
        # virtualenv < 20 overwrites site.py without getsitepackages
        # fallback on get_purelib/get_platlib.
        # this is known to miss things, but shouldn't in the cases
        # where getsitepackages() has been removed (inside a virtualenv)
        system_sites = [get_purelib(), get_platlib()]
    return {os.path.normcase(path) for path in system_sites}


class BuildEnvironment(OverlayBuildEnvironment):
    """Creates and manages an isolated environment to install build deps"""

    def __init__(self) -> None:
        temp_dir = TempDirectory(kind=tempdir_kinds.BUILD_ENV, globally_managed=True)

        self._prefixes = OrderedDict(
            (name, Prefix(os.path.join(temp_dir.path, name)))
            for name in ("normal", "overlay")
        )

        self._bin_dirs: List[str] = []
        self._lib_dirs: List[str] = []
        for prefix in reversed(list(self._prefixes.values())):
            self._bin_dirs.append(prefix.bin_dir)
            self._lib_dirs.extend(prefix.lib_dirs)

        # Customize site to:
        # - ensure .pth files are honored
        # - prevent access to system site packages
        system_sites = _get_system_sitepackages()

        self._site_dir = os.path.join(temp_dir.path, "site")
        if not os.path.exists(self._site_dir):
            os.mkdir(self._site_dir)
        with open(
            os.path.join(self._site_dir, "sitecustomize.py"), "w", encoding="utf-8"
        ) as fp:
            fp.write(
                textwrap.dedent(
                    """
                import os, site, sys

                # First, drop system-sites related paths.
                original_sys_path = sys.path[:]
                known_paths = set()
                for path in {system_sites!r}:
                    site.addsitedir(path, known_paths=known_paths)
                system_paths = set(
                    os.path.normcase(path)
                    for path in sys.path[len(original_sys_path):]
                )
                original_sys_path = [
                    path for path in original_sys_path
                    if os.path.normcase(path) not in system_paths
                ]
                sys.path = original_sys_path

                # Second, add lib directories.
                # ensuring .pth file are processed.
                for path in {lib_dirs!r}:
                    assert not path in sys.path
                    site.addsitedir(path)
                """
                ).format(system_sites=system_sites, lib_dirs=self._lib_dirs)
            )

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Collection[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        prefix = self._prefixes[prefix_as_string]
        assert not prefix.setup
        prefix.setup = True
        if not requirements:
            return
        self._install_requirements(
            get_runnable_pip(),
            finder,
            requirements,
            prefix,
            kind=kind,
        )

    @staticmethod
    def _install_requirements(
        pip_runnable: str,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix: Prefix,
        *,
        kind: str,
    ) -> None:
        args = [
            sys.executable,
            pip_runnable,
            "install",
            "--ignore-installed",
            "--no-user",
            "--prefix",
            prefix.path,
            "--no-warn-script-location",
            *iter_install_flags(finder),
            "--",
            *requirements,
        ]
        extra_environ = {"_PIP_STANDALONE_CERT": where()}
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
                extra_environ=extra_environ,
            )
