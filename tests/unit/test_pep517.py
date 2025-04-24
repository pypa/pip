import os
from pathlib import Path
from textwrap import dedent
from typing import Tuple

import pytest

from pip._internal.exceptions import InstallationError, InvalidPyProjectBuildRequires
from pip._internal.req import InstallRequirement

from tests.lib import TestData


@pytest.mark.parametrize(
    "source, expected",
    [
        ("pep517_setup_and_pyproject", True),
        ("pep517_setup_only", False),
        ("pep517_pyproject_only", True),
    ],
)
def test_use_pep517(shared_data: TestData, source: str, expected: bool) -> None:
    """
    Test that we choose correctly between PEP 517 and legacy code paths
    """
    src = shared_data.src.joinpath(source)
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(src)  # make req believe it has been unpacked
    req.load_pyproject_toml()
    assert req.use_pep517 is expected


def test_use_pep517_rejects_setup_cfg_only(shared_data: TestData) -> None:
    """
    Test that projects with setup.cfg but no pyproject.toml are rejected.
    """
    src = shared_data.src.joinpath("pep517_setup_cfg_only")
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(src)  # make req believe it has been unpacked
    with pytest.raises(InstallationError) as e:
        req.load_pyproject_toml()
    err_msg = e.value.args[0]
    assert (
        "does not appear to be a Python project: "
        "neither 'setup.py' nor 'pyproject.toml' found" in err_msg
    )


@pytest.mark.parametrize(
    "source, msg",
    [
        ("pep517_setup_and_pyproject", "specifies a build backend"),
        ("pep517_pyproject_only", "does not have a setup.py"),
    ],
)
def test_disabling_pep517_invalid(shared_data: TestData, source: str, msg: str) -> None:
    """
    Test that we fail if we try to disable PEP 517 when it's not acceptable
    """
    src = shared_data.src.joinpath(source)
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(src)  # make req believe it has been unpacked

    # Simulate --no-use-pep517
    req.use_pep517 = False

    with pytest.raises(InstallationError) as e:
        req.load_pyproject_toml()

    err_msg = e.value.args[0]
    assert "Disabling PEP 517 processing is invalid" in err_msg
    assert msg in err_msg


@pytest.mark.parametrize(
    "spec", [("./foo",), ("git+https://example.com/pkg@dev#egg=myproj",)]
)
def test_pep517_parsing_checks_requirements(tmpdir: Path, spec: Tuple[str]) -> None:
    tmpdir.joinpath("pyproject.toml").write_text(
        dedent(
            f"""
            [build-system]
            requires = [{spec[0]!r}]
            build-backend = "foo"
            """
        )
    )
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(tmpdir)  # make req believe it has been unpacked

    with pytest.raises(InvalidPyProjectBuildRequires) as e:
        req.load_pyproject_toml()

    error = e.value

    assert str(req) in error.message
    assert error.context
    assert "build-system.requires" in error.context
    assert "contains an invalid requirement" in error.context
    assert error.hint_stmt
    assert "PEP 518" in error.hint_stmt
