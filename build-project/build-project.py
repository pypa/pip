#!/usr/bin/env python3
"""Build pip using pinned build requirements."""

import subprocess
import tempfile
import venv
from os import PathLike
from pathlib import Path
from types import SimpleNamespace
from typing import Union


class EnvBuilder(venv.EnvBuilder):
    """A subclass of venv.EnvBuilder that exposes the python executable command."""

    def ensure_directories(
        self, env_dir: Union[str, bytes, "PathLike[str]", "PathLike[bytes]"]
    ) -> SimpleNamespace:
        context = super().ensure_directories(env_dir)
        self.env_exec_cmd = context.env_exec_cmd
        return context


def get_git_head_timestamp() -> str:
    return subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--pretty=format:%ct",
        ],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def main() -> None:
    with tempfile.TemporaryDirectory() as build_env:
        env_builder = EnvBuilder(with_pip=True)
        # If this venv creation step fails, you may be hitting
        # https://github.com/astral-sh/python-build-standalone/issues/381
        # Try running with a another Python distribution.
        env_builder.create(build_env)
        subprocess.run(
            [
                env_builder.env_exec_cmd,
                "-Im",
                "pip",
                "install",
                "--no-deps",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                Path(__file__).parent / "build-requirements.txt",
            ],
            check=True,
        )
        subprocess.run(
            [
                env_builder.env_exec_cmd,
                "-Im",
                "build",
                "--no-isolation",
            ],
            check=True,
            env={"SOURCE_DATE_EPOCH": get_git_head_timestamp()},
            cwd=Path(__file__).parent.parent,
        )


if __name__ == "__main__":
    main()
