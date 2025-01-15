#!/usr/bin/env python3
"""Build pip using pinned build requirements."""

import subprocess
import sys
import tempfile
from pathlib import Path


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
        subprocess.run(
            [
                sys.executable,
                "-m",
                "venv",
                build_env,
            ],
            check=True,
        )
        build_python = Path(build_env) / "bin" / "python"
        subprocess.run(
            [
                build_python,
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
                build_python,
                "-Im",
                "build",
                "--no-isolation",
            ],
            check=True,
            env={"SOURCE_DATE_EPOCH": get_git_head_timestamp()},
        )


if __name__ == "__main__":
    main()
