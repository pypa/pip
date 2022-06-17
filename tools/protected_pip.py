"""Maintain and use a protected copy of pip for use during development.

The protected copy of pip can be used to manipulate the environment while keeping a
potentially-non-functional installation of in-development pip in the development virtual
environment.

This allows for setting up the test environments and exercising the in-development code,
even when it is not functional-enough to install the packages for setting up the
environment that it is being used it.
"""

import os
import shutil
import subprocess
import sys
from glob import glob
from typing import List

VIRTUAL_ENV = os.environ["VIRTUAL_ENV"]
PROTECTED_PIP_DIR = os.path.join(VIRTUAL_ENV, "pip")


def _setup_protected_pip() -> None:
    # This setup happens before any development version of pip is installed in this
    # environment. So, at this point, the existing pip installation should be from a
    # stable release and can be safely used to create the protected copy.
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "-t",
            PROTECTED_PIP_DIR,
            "pip",
        ]
    )
    # Make it impossible for pip (and other Python tooling) to discover this protected
    # installation of pip using the metadata, by deleting the metadata.
    shutil.rmtree(glob(os.path.join(PROTECTED_PIP_DIR, "pip-*.dist-info"))[0])


def main(args: List[str]) -> None:
    # If we don't have a protected pip, let's set it up.
    if not os.path.exists(PROTECTED_PIP_DIR):
        _setup_protected_pip()

    # Run Python, with the protected pip copy on PYTHONPATH.
    pypath_env = os.environ.get("PYTHONPATH", "")
    old_PYTHONPATH_entries = pypath_env.split(os.pathsep) if pypath_env else []
    new_PYTHONPATH = os.pathsep.join([PROTECTED_PIP_DIR] + old_PYTHONPATH_entries)

    subprocess.check_call(
        [sys.executable, "-m", "pip"] + args,
        env={"PYTHONPATH": new_PYTHONPATH},
    )


if __name__ == "__main__":
    main(sys.argv[1:])
