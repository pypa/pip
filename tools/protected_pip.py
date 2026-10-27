from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Iterable
from glob import glob

VIRTUAL_ENV = os.environ["VIRTUAL_ENV"]
TOX_PIP_DIR = os.path.join(VIRTUAL_ENV, "pip")
# pip 26.2.2 includes the certifi fix for the emSign compromise.
PIP_REQUIREMENT = "pip>=26.2.2"


def pip(args: Iterable[str | pathlib.Path]) -> None:
    """Run pip through a cached copy satisfying the bootstrap requirement."""
    # Bootstrap from the cached copy if the session's pip has been removed.
    pypath_env = os.environ.get("PYTHONPATH")
    pypath = pypath_env.split(os.pathsep) if pypath_env is not None else []
    pypath.insert(0, TOX_PIP_DIR)
    os.environ["PYTHONPATH"] = os.pathsep.join(pypath)

    requirement_file = pathlib.Path(TOX_PIP_DIR, "requirement.txt")
    # Refresh existing caches when the required pip version changes.
    if (
        not requirement_file.exists()
        or requirement_file.read_text(encoding="utf-8").strip() != PIP_REQUIREMENT
    ):
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                "--upgrade",
                "-t",
                TOX_PIP_DIR,
                PIP_REQUIREMENT,
            ]
        )
        for dist_info in glob(os.path.join(TOX_PIP_DIR, "pip-*.dist-info")):
            shutil.rmtree(dist_info)
        requirement_file.write_text(PIP_REQUIREMENT + "\n", encoding="utf-8")

    subprocess.check_call([sys.executable, "-m", "pip", *(os.fspath(a) for a in args)])


if __name__ == "__main__":
    pip(sys.argv[1:])
