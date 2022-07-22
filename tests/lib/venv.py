import compileall
import os
import shutil
import sysconfig
import textwrap
import venv as _venv
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import virtualenv as _virtualenv

if TYPE_CHECKING:
    # Literal was introduced in Python 3.8.
    from typing import Literal

    VirtualEnvironmentType = Literal["virtualenv", "venv"]
else:
    VirtualEnvironmentType = str


class VirtualEnvironment:
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(
        self,
        location: Path,
        template: Optional["VirtualEnvironment"] = None,
        venv_type: Optional[VirtualEnvironmentType] = None,
    ):
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
        self._sitecustomize: Optional[str] = None
        self._update_paths()
        self._create()

    def _update_paths(self) -> None:
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
            # Clone virtual environment from template.
            shutil.copytree(self._template.location, self.location, symlinks=True)
            self._sitecustomize = self._template.sitecustomize
            self._user_site_packages = self._template.user_site_packages
        else:
            # Create a new virtual environment.
            if self._venv_type == "virtualenv":
                _virtualenv.cli_run(
                    [
                        "--no-pip",
                        "--no-wheel",
                        "--no-setuptools",
                        os.fspath(self.location),
                    ],
                )
            elif self._venv_type == "venv":
                builder = _venv.EnvBuilder()
                context = builder.ensure_directories(self.location)
                builder.create_configuration(context)
                builder.setup_python(context)
                self.site.mkdir(parents=True, exist_ok=True)
            self.sitecustomize = self._sitecustomize
            self.user_site_packages = self._user_site_packages

    def _customize_site(self) -> None:
        # Enable user site (before system).
        contents = textwrap.dedent(
            f"""
            import os, site, sys
            if not os.environ.get('PYTHONNOUSERSITE', False):
                site.ENABLE_USER_SITE = {self._user_site_packages}
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
                if {self._user_site_packages}:
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

    def move(self, location: Union[Path, str]) -> None:
        shutil.move(os.fspath(self.location), location)
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
        self._customize_site()
