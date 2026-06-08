from __future__ import annotations

import compileall
import os
import shutil
import subprocess
import sys
import sysconfig
import venv as _venv
from pathlib import Path
from typing import Literal

import virtualenv as _virtualenv

VirtualEnvironmentType = Literal["virtualenv", "venv"]


# sitecustomize for test venvs: enable user-site and order it before the
# system sites. To do that the system-site paths are dropped and then re-added
# after user-site. The paths a system site contributes (its directory plus any
# its .pth files add) are read from the .pth files directly; this mirrors
# pip._internal.build_env._get_system_paths.
_USER_SITE_CUSTOMIZE_TEMPLATE = """\
import os, site, sys

if not os.environ.get("PYTHONNOUSERSITE", False):
    site.ENABLE_USER_SITE = {user_site}

    system_paths = set()
    for sitedir in site.getsitepackages():
        system_paths.add(os.path.normcase(sitedir))
        try:
            names = os.listdir(sitedir)
        except OSError:
            continue
        for name in names:
            if name.startswith(".") or not name.endswith(".pth"):
                continue
            try:
                with open(os.path.join(sitedir, name), "rb") as f:
                    content = f.read()
            except OSError:
                continue
            for line in content.decode("utf-8-sig", "replace").splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "import ", "import\\t")):
                    continue
                path = os.path.abspath(os.path.join(sitedir, line))
                system_paths.add(os.path.normcase(path))

    sys.path = [p for p in sys.path if os.path.normcase(p) not in system_paths]

    if {user_site}:
        site.addsitedir(site.getusersitepackages())
    for path in site.getsitepackages():
        site.addsitedir(path)
"""


class VirtualEnvironment:
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(
        self,
        location: Path,
        template: VirtualEnvironment | None = None,
        venv_type: VirtualEnvironmentType | None = None,
    ) -> None:
        self.location = location
        assert template is None or venv_type is None
        self._venv_type: VirtualEnvironmentType
        if template is not None:
            self._venv_type = template._venv_type
        elif venv_type is not None:
            self._venv_type = venv_type
        else:
            self._venv_type = "virtualenv"
        self._user_site_packages = False
        self._template = template
        self._sitecustomize: str | None = None
        self._update_paths()
        self._create()

    @property
    def _legacy_virtualenv(self) -> bool:
        if self._venv_type != "virtualenv":
            return False
        return int(_virtualenv.__version__.split(".", 1)[0]) < 20

    def __update_paths_legacy(self) -> None:
        home, lib, inc, bin = _virtualenv.path_locations(self.location)  # type: ignore[attr-defined]
        self.bin = Path(bin)
        self.site = Path(lib) / "site-packages"
        # Workaround for https://github.com/pypa/virtualenv/issues/306
        if hasattr(sys, "pypy_version_info"):
            version_dir = str(sys.version_info.major)
            self.lib = Path(home, "lib-python", version_dir)
        else:
            self.lib = Path(lib)

    def _update_paths(self) -> None:
        if self._legacy_virtualenv:
            self.__update_paths_legacy()
            return
        bases = {
            "installed_base": self.location,
            "installed_platbase": self.location,
            "base": self.location,
            "platbase": self.location,
        }
        paths = sysconfig.get_paths(vars=bases)
        self.bin = Path(paths["scripts"])
        self.site = Path(paths["purelib"])
        self.lib = Path(paths["stdlib"])

    def __repr__(self) -> str:
        return f"<VirtualEnvironment {self.location}>"

    def _create(self, clear: bool = False) -> None:
        if clear:
            shutil.rmtree(self.location)
        if self._template:
            # On Windows, calling `_virtualenv.path_locations(target)`
            # will have created the `target` directory...
            if (
                self._legacy_virtualenv
                and sys.platform == "win32"
                and self.location.exists()
            ):
                self.location.rmdir()
            # Clone virtual environment from template.
            shutil.copytree(self._template.location, self.location, symlinks=True)
            self._sitecustomize = self._template.sitecustomize
            self._user_site_packages = self._template.user_site_packages
        else:
            # Create a new virtual environment.
            if self._legacy_virtualenv:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "virtualenv",
                        "--no-pip",
                        "--no-wheel",
                        "--no-setuptools",
                        os.fspath(self.location),
                    ]
                )
                self._fix_legacy_virtualenv_site_module()
            elif self._venv_type == "virtualenv":
                _virtualenv.cli_run(
                    [
                        "--no-pip",
                        "--no-setuptools",
                        os.fspath(self.location),
                    ],
                )
            elif self._venv_type == "venv":
                builder = _venv.EnvBuilder()
                context = builder.ensure_directories(os.fspath(self.location))
                builder.create_configuration(context)
                builder.setup_python(context)
                self.site.mkdir(parents=True, exist_ok=True)
            else:
                raise RuntimeError(f"Unsupported venv type {self._venv_type!r}")
            self.sitecustomize = self._sitecustomize
            self.user_site_packages = self._user_site_packages

    def _fix_legacy_virtualenv_site_module(self) -> None:
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
        if self._legacy_virtualenv:
            contents = ""
        else:
            contents = _USER_SITE_CUSTOMIZE_TEMPLATE.format(
                user_site=self._user_site_packages
            )
        if self._sitecustomize is not None:
            contents += "\n" + self._sitecustomize
        sitecustomize = self.site / "sitecustomize.py"
        sitecustomize.write_text(contents)
        # Make sure bytecode is up-to-date too.
        assert compileall.compile_file(str(sitecustomize), quiet=1, force=True)

    def _rewrite_pyvenv_cfg(self, replacements: dict[str, str]) -> None:
        pyvenv_cfg = self.location.joinpath("pyvenv.cfg")
        lines = pyvenv_cfg.read_text(encoding="utf-8").splitlines()

        def maybe_replace_line(line: str) -> str:
            key = line.split("=", 1)[0].strip()
            try:
                value = replacements[key]
            except KeyError:  # No need to replace.
                return line
            return f"{key} = {value}"

        lines = [maybe_replace_line(line) for line in lines]
        pyvenv_cfg.write_text("\n".join(lines), encoding="utf-8")

    def clear(self) -> None:
        self._create(clear=True)

    def move(self, location: Path | str) -> None:
        shutil.move(os.fspath(self.location), location)
        self.location = Path(location)
        self._update_paths()

    @property
    def sitecustomize(self) -> str | None:
        return self._sitecustomize

    @sitecustomize.setter
    def sitecustomize(self, value: str | None) -> None:
        self._sitecustomize = value
        self._customize_site()

    @property
    def user_site_packages(self) -> bool:
        return self._user_site_packages

    @user_site_packages.setter
    def user_site_packages(self, value: bool) -> None:
        self._user_site_packages = value
        if self._legacy_virtualenv:
            marker = self.lib / "no-global-site-packages.txt"
            if self._user_site_packages:
                marker.unlink()
            else:
                marker.touch()
        else:
            self._rewrite_pyvenv_cfg(
                {"include-system-site-packages": str(bool(value)).lower()}
            )
            self._customize_site()
