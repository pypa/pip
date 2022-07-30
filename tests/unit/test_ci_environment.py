# See https://github.com/pypa/pip/issues/11320
#
# The CI environment seems to have an issue that results in packages from
# the test environment "leaking" into a supposedly isolated stdlib venv.
#
# This is a failing test that demonstrates the issue. Note that it appears
# to only fail in CI, not when run locally.

import os
import subprocess
from pathlib import Path
from venv import EnvBuilder


def test_ci_fails_to_isolate_venv(
    tmpdir: Path,
) -> None:
    env_path = tmpdir / "venv"
    env = EnvBuilder(with_pip=False)
    env.create(env_path)
    for possible in ("bin/python", "Scripts/python.exe"):
        env_python = env_path / possible
        if env_python.exists():
            break
    else:
        assert False, "Could not find venv's Python interpreter"
    proc = subprocess.run([os.fspath(env_python), "-c", "import pytest"])
    assert proc.returncode != 0, "The pytest module is visible in the venv"
