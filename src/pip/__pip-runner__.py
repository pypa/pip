"""Execute exactly this copy of pip, within a different environment.

This file is named as it is, to ensure that this module can't be imported via
an import statement.
"""

import importlib.util
import runpy
import sys
import types
from importlib.machinery import ModuleSpec
from os.path import dirname, join
from typing import Optional, Sequence, Union

PIP_SOURCES_ROOT = dirname(dirname(dirname(__file__)))


class PipImportRedirectingFinder:
    @classmethod
    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[Union[bytes, str]]] = None,
        target: Optional[types.ModuleType] = None,
    ) -> Optional[ModuleSpec]:
        if not fullname.startswith("pip."):
            return None

        # Import pip from the source directory of this file
        location = join(PIP_SOURCES_ROOT, *fullname.split("."))
        return importlib.util.spec_from_file_location(fullname, location)


sys.meta_path.insert(0, PipImportRedirectingFinder())

assert __name__ == "__main__", "Cannot run __pip-runner__.py as a non-main module"
runpy.run_module("pip", run_name="__main__")
