import json
import os
from pathlib import Path
from venv import EnvBuilder

from tests.lib import PipTestEnvironment, TestData


def test_python_interpreter(
    script: PipTestEnvironment,
    tmpdir: Path,
    shared_data: TestData,
) -> None:
    env_path = os.fsdecode(tmpdir / "venv")
    env = EnvBuilder(with_pip=False)
    env.create(env_path)

    result = script.pip("--python", env_path, "list", "--format=json")
    assert json.loads(result.stdout) == []
    script.pip(
        "--python",
        env_path,
        "install",
        "-f",
        shared_data.find_links,
        "--no-index",
        "simplewheel==1.0",
    )
    result = script.pip("--python", env_path, "list", "--format=json")
    assert json.loads(result.stdout) == [{"name": "simplewheel", "version": "1.0"}]
    script.pip("--python", env_path, "uninstall", "simplewheel", "--yes")
    result = script.pip("--python", env_path, "list", "--format=json")
    assert json.loads(result.stdout) == []
