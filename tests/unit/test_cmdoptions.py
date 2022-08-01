import os
from pathlib import Path
from typing import Optional, Tuple
from venv import EnvBuilder

import pytest

from pip._internal.cli.cmdoptions import _convert_python_version
from pip._internal.cli.main_parser import identify_python_interpreter


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", (None, None)),
        ("2", ((2,), None)),
        ("3", ((3,), None)),
        ("3.7", ((3, 7), None)),
        ("3.7.3", ((3, 7, 3), None)),
        # Test strings without dots of length bigger than 1.
        ("34", ((3, 4), None)),
        # Test a 2-digit minor version.
        ("310", ((3, 10), None)),
        # Test some values that fail to parse.
        ("ab", ((), "each version part must be an integer")),
        ("3a", ((), "each version part must be an integer")),
        ("3.7.a", ((), "each version part must be an integer")),
        ("3.7.3.1", ((), "at most three version parts are allowed")),
    ],
)
def test_convert_python_version(
    value: str, expected: Tuple[Optional[Tuple[int, ...]], Optional[str]]
) -> None:
    actual = _convert_python_version(value)
    assert actual == expected, f"actual: {actual!r}"


def test_identify_python_interpreter_venv(tmpdir: Path) -> None:
    env_path = tmpdir / "venv"
    env = EnvBuilder(with_pip=False)
    env.create(env_path)

    # Passing a virtual environment returns the Python executable
    interp = identify_python_interpreter(os.fspath(env_path))
    assert interp is not None
    assert Path(interp).exists()

    # Passing an executable returns it
    assert identify_python_interpreter(interp) == interp

    # Passing a non-existent file returns None
    assert identify_python_interpreter(str(tmpdir / "nonexistent")) is None
