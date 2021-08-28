import compileall
import shutil
import subprocess
import sys
import textwrap
import venv as _venv
from typing import TYPE_CHECKING, Optional

import virtualenv as _virtualenv

from .path import Path

if TYPE_CHECKING:
    # Literal was introduced in Python 3.8.
    from typing import Literal


class VirtualEnvironment:
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(
        self,
        location: str,
        template: Optional["VirtualEnvironment"] = None,
        venv_type: 'Literal[None, "virtualenv", "venv"]' = None,
    ):
        self.location = Path(location)
        assert template is None or venv_type is None
        self._venv_type: Literal["virtualenv", "venv"]
        if template is not None:
            self._venv_type = template._venv_type
        elif venv_type is not None:
            self._venv_type = venv_type
        else:
            self._venv_type = "virtualenv"
        self._user_site_packages = False
        self._template = template
        self._sitecustomize: Optional[str] = None
        self._update_paths()
        self._create()

    def _update_paths(self) -> None:
        home, lib, inc, bin = _virtualenv.path_locations(self.location)
        self.bin = Path(bin)
        self.site = Path(lib) / "site-packages"
        # Workaround for https://github.com/pypa/virtualenv/issues/306
        if hasattr(sys, "pypy_version_info"):
            version_dir = str(sys.version_info.major)
            self.lib = Path(home, "lib-python", version_dir)
        else:
            self.lib = Path(lib)

    def __repr__(self) -> str:
        return f"<VirtualEnvironment {self.location}>"

    def _create(self, clear: bool = False) -> None:
        if clear:
            shutil.rmtree(self.location)
        if self._template:
            # On Windows, calling `_virtualenv.path_locations(target)`
            # will have created the `target` directory...
            if sys.platform == "win32" and self.location.exists():
                self.location.rmdir()
            # Clone virtual environment from template.
            shutil.copytree(self._template.location, self.location, symlinks=True)
            self._sitecustomize = self._template.sitecustomize
            self._user_site_packages = self._template.user_site_packages
        else:
            # Create a new virtual environment.
            if self._venv_type == "virtualenv":
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "virtualenv",
                        "--no-pip",
                        "--no-wheel",
                        "--no-setuptools",
                        str(self.location),
                    ]
                )
                self._fix_virtualenv_site_module()
            elif self._venv_type == "venv":
                builder = _venv.EnvBuilder()
                context = builder.ensure_directories(self.location)
                builder.create_configuration(context)
                builder.setup_python(context)
                self.site.mkdir(parents=True, exist_ok=True)
            self.sitecustomize = self._sitecustomize
            self.user_site_packages = self._user_site_packages

    def _fix_virtualenv_site_module(self) -> None:
        # Patch `site.py` so user site work as expected.
        site_py = self.lib / "site.py"
        with open(site_py) as fp:
            site_contents = fp.read()
        for pattern, replace in (
            (
                # Ensure enabling user site does not result in adding
                # the real site-packages' directory to `sys.path`.
                ("\ndef virtual_addsitepackages(known_paths):\n"),
                (
                    "\ndef virtual_addsitepackages(known_paths):\n"
                    "    return known_paths\n"
                ),
            ),
            (
                # Fix sites ordering: user site must be added before system.
                (
                    "\n    paths_in_sys = addsitepackages(paths_in_sys)"
                    "\n    paths_in_sys = addusersitepackages(paths_in_sys)\n"
                ),
                (
                    "\n    paths_in_sys = addusersitepackages(paths_in_sys)"
                    "\n    paths_in_sys = addsitepackages(paths_in_sys)\n"
                ),
            ),
        ):
            assert pattern in site_contents
            site_contents = site_contents.replace(pattern, replace)
        with open(site_py, "w") as fp:
            fp.write(site_contents)
        # Make sure bytecode is up-to-date too.
        assert compileall.compile_file(str(site_py), quiet=1, force=True)

    def _customize_site(self) -> None:
        contents = ""
        if self._venv_type == "venv":
            # Enable user site (before system).
            contents += textwrap.dedent(
                """
                import os, site, sys

                if not os.environ.get('PYTHONNOUSERSITE', False):

                    site.ENABLE_USER_SITE = True

                    # First, drop system-sites related paths.
                    original_sys_path = sys.path[:]
                    known_paths = set()
                    for path in site.getsitepackages():
                        site.addsitedir(path, known_paths=known_paths)
                    system_paths = sys.path[len(original_sys_path):]
                    for path in system_paths:
                        if path in original_sys_path:
                            original_sys_path.remove(path)
                    sys.path = original_sys_path

                    # Second, add user-site.
                    site.addsitedir(site.getusersitepackages())

                    # Third, add back system-sites related paths.
                    for path in site.getsitepackages():
                        site.addsitedir(path)
                """
            ).strip()
        if self._sitecustomize is not None:
            contents += "\n" + self._sitecustomize
        sitecustomize = self.site / "sitecustomize.py"
        sitecustomize.write_text(contents)
        # Make sure bytecode is up-to-date too.
        assert compileall.compile_file(str(sitecustomize), quiet=1, force=True)

    def clear(self) -> None:
        self._create(clear=True)

    def move(self, location: str) -> None:
        shutil.move(self.location, location)
        self.location = Path(location)
        self._update_paths()

    @property
    def sitecustomize(self) -> Optional[str]:
        return self._sitecustomize

    @sitecustomize.setter
    def sitecustomize(self, value: str) -> None:
        self._sitecustomize = value
        self._customize_site()

    @property
    def user_site_packages(self) -> bool:
        return self._user_site_packages

    @user_site_packages.setter
    def user_site_packages(self, value: bool) -> None:
        self._user_site_packages = value
        if self._venv_type == "virtualenv":
            marker = self.lib / "no-global-site-packages.txt"
            if self._user_site_packages:
                marker.unlink()
            else:
                marker.touch()
        elif self._venv_type == "venv":
            self._customize_site()
