"""Execute exactly this copy of pip, within a different environment.

This file is named as it is, to ensure that this module can't be imported via
an import statement.
"""

import runpy
import sys
import types
from importlib.machinery import ModuleSpec, PathFinder
from os.path import dirname
from typing import Optional, Sequence, Union

PIP_SOURCES_ROOT = dirname(dirname(__file__))
# Copied from setup.py
PYTHON_REQUIRES = ">=3.7"


class PipImportRedirectingFinder:
    @classmethod
    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[Union[bytes, str]]] = None,
        target: Optional[types.ModuleType] = None,
    ) -> Optional[ModuleSpec]:
        if fullname != "pip":
            return None

        spec = PathFinder.find_spec(fullname, [PIP_SOURCES_ROOT], target)
        assert spec, (PIP_SOURCES_ROOT, fullname)
        return spec


def check_python_version() -> None:
    # Import here to ensure the imports happen after the sys.meta_path change.
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.version import Version

    py_ver = Version("{0.major}.{0.minor}.{0.micro}".format(sys.version_info))
    if py_ver not in SpecifierSet(PYTHON_REQUIRES):
        raise SystemExit(
            f"This version of pip does not support python {py_ver} "
            f"(requires {PYTHON_REQUIRES})"
        )


# TODO https://github.com/pypa/pip/issues/11294
sys.meta_path.insert(0, PipImportRedirectingFinder())

assert __name__ == "__main__", "Cannot run __pip-runner__.py as a non-main module"
check_python_version()
runpy.run_module("pip", run_name="__main__", alter_sys=True)
