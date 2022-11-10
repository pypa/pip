import os
import pathlib
import shutil
import subprocess
import sys
from glob import glob
from typing import Iterable, Union

VIRTUAL_ENV = os.environ["VIRTUAL_ENV"]
TOX_PIP_DIR = os.path.join(VIRTUAL_ENV, "pip")


def pip(args: Iterable[Union[str, pathlib.Path]]) -> None:
    # First things first, get a recent (stable) version of pip.
    if not os.path.exists(TOX_PIP_DIR):
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                "-t",
                TOX_PIP_DIR,
                "pip",
            ]
        )
        shutil.rmtree(glob(os.path.join(TOX_PIP_DIR, "pip-*.dist-info"))[0])
    # And use that version.
    pypath_env = os.environ.get("PYTHONPATH")
    pypath = pypath_env.split(os.pathsep) if pypath_env is not None else []
    pypath.insert(0, TOX_PIP_DIR)
    os.environ["PYTHONPATH"] = os.pathsep.join(pypath)
    subprocess.check_call([sys.executable, "-m", "pip", *(os.fspath(a) for a in args)])


if __name__ == "__main__":
    pip(sys.argv[1:])
