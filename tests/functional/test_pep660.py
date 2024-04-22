import os
from pathlib import Path
from typing import Any, Dict

import tomli_w

from tests.lib import PipTestEnvironment

SETUP_PY = """
from setuptools import setup

setup()
"""

SETUP_CFG = """
[metadata]
name = project
version = 1.0.0
"""

BACKEND_WITHOUT_PEP660 = """
from setuptools.build_meta import (
    build_wheel as _build_wheel,
    prepare_metadata_for_build_wheel as _prepare_metadata_for_build_wheel,
    get_requires_for_build_wheel as _get_requires_for_build_wheel,
)

def get_requires_for_build_wheel(config_settings=None):
    with open("log.txt", "a") as f:
        print(":get_requires_for_build_wheel called", file=f)
    return _get_requires_for_build_wheel(config_settings)

def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    with open("log.txt", "a") as f:
        print(":prepare_metadata_for_build_wheel called", file=f)
    return _prepare_metadata_for_build_wheel(metadata_directory, config_settings)

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    with open("log.txt", "a") as f:
        print(f":build_wheel called with config_settings={config_settings}", file=f)
    return _build_wheel(wheel_directory, config_settings, metadata_directory)
"""

# fmt: off
BACKEND_WITH_PEP660 = BACKEND_WITHOUT_PEP660 + """
def get_requires_for_build_editable(config_settings=None):
    with open("log.txt", "a") as f:
        print(":get_requires_for_build_editable called", file=f)
    return _get_requires_for_build_wheel(config_settings)

def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    with open("log.txt", "a") as f:
        print(":prepare_metadata_for_build_editable called", file=f)
    return _prepare_metadata_for_build_wheel(metadata_directory, config_settings)

def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    with open("log.txt", "a") as f:
        print(f":build_editable called with config_settings={config_settings}", file=f)
    return _build_wheel(wheel_directory, config_settings, metadata_directory)
"""
# fmt: on


def _make_project(
    tmpdir: Path, backend_code: str, with_setup_py: bool, with_pyproject: bool = True
) -> Path:
    project_dir = tmpdir / "project"
    project_dir.mkdir()
    project_dir.joinpath("setup.cfg").write_text(SETUP_CFG)
    if with_setup_py:
        project_dir.joinpath("setup.py").write_text(SETUP_PY)
    if backend_code:
        assert with_pyproject
        buildsys: Dict[str, Any] = {"requires": ["setuptools", "wheel"]}
        buildsys["build-backend"] = "test_backend"
        buildsys["backend-path"] = ["."]
        data = tomli_w.dumps({"build-system": buildsys})
        project_dir.joinpath("pyproject.toml").write_text(data)
        project_dir.joinpath("test_backend.py").write_text(backend_code)
    elif with_pyproject:
        project_dir.joinpath("pyproject.toml").touch()
    project_dir.joinpath("log.txt").touch()
    return project_dir


def _assert_hook_called(project_dir: Path, hook: str) -> None:
    log = project_dir.joinpath("log.txt").read_text()
    assert f":{hook} called" in log, f"{hook} has not been called"


def _assert_hook_called_with_config_settings(
    project_dir: Path, hook: str, config_settings: Dict[str, str]
) -> None:
    log = project_dir.joinpath("log.txt").read_text()
    assert f":{hook} called" in log, f"{hook} has not been called"
    assert (
        f":{hook} called with config_settings={config_settings}" in log
    ), f"{hook} has not been called with the expected config settings:\n{log}"


def _assert_hook_not_called(project_dir: Path, hook: str) -> None:
    log = project_dir.joinpath("log.txt").read_text()
    assert f":{hook} called" not in log, f"{hook} should not have been called"


def test_install_pep517_basic(tmpdir: Path, script: PipTestEnvironment) -> None:
    """
    Check that the test harness we have in this file is sane.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITHOUT_PEP660, with_setup_py=False)
    script.pip(
        "install",
        "--no-index",
        "--no-build-isolation",
        project_dir,
    )
    _assert_hook_called(project_dir, "prepare_metadata_for_build_wheel")
    _assert_hook_called(project_dir, "build_wheel")


def test_install_pep660_basic(tmpdir: Path, script: PipTestEnvironment) -> None:
    """
    Test with backend that supports build_editable.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITH_PEP660, with_setup_py=False)
    result = script.pip(
        "install",
        "--no-index",
        "--no-build-isolation",
        "--editable",
        project_dir,
        "--config-setting",
        "x=y",
    )
    _assert_hook_called(project_dir, "prepare_metadata_for_build_editable")
    _assert_hook_called_with_config_settings(project_dir, "build_editable", {"x": "y"})
    assert (
        result.test_env.site_packages.joinpath("project.egg-link")
        not in result.files_created
    ), "a .egg-link file should not have been created"


def test_install_pep660_from_reqs_file(
    tmpdir: Path, script: PipTestEnvironment
) -> None:
    """
    Test with backend that supports build_editable.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITH_PEP660, with_setup_py=False)
    reqs_file = tmpdir / "requirements.txt"
    reqs_file.write_text(f"-e {project_dir.as_uri()} --config-setting x=y\n")
    result = script.pip(
        "install",
        "--no-index",
        "--no-build-isolation",
        "-r",
        reqs_file,
    )
    _assert_hook_called(project_dir, "prepare_metadata_for_build_editable")
    _assert_hook_called_with_config_settings(project_dir, "build_editable", {"x": "y"})
    assert (
        result.test_env.site_packages.joinpath("project.egg-link")
        not in result.files_created
    ), "a .egg-link file should not have been created"


def test_install_no_pep660_setup_py_fallback(
    tmpdir: Path, script: PipTestEnvironment
) -> None:
    """
    Test that we fall back to setuptools develop when using a backend that
    does not support build_editable. Since there is a pyproject.toml,
    the prepare_metadata_for_build_wheel hook is called.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITHOUT_PEP660, with_setup_py=True)
    result = script.pip(
        "install",
        "--no-index",
        "--no-build-isolation",
        "--editable",
        project_dir,
        allow_stderr_warning=False,
    )
    _assert_hook_called(project_dir, "prepare_metadata_for_build_wheel")
    assert (
        result.test_env.site_packages.joinpath("project.egg-link")
        in result.files_created
    ), "a .egg-link file should have been created"


def test_install_no_pep660_setup_cfg_fallback(
    tmpdir: Path, script: PipTestEnvironment
) -> None:
    """
    Test that we fall back to setuptools develop when using a backend that
    does not support build_editable. Since there is a pyproject.toml,
    the prepare_metadata_for_build_wheel hook is called.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITHOUT_PEP660, with_setup_py=False)
    result = script.pip(
        "install",
        "--no-index",
        "--no-build-isolation",
        "--editable",
        project_dir,
        allow_stderr_warning=False,
    )
    print(result.stdout, result.stderr)
    _assert_hook_called(project_dir, "prepare_metadata_for_build_wheel")
    assert (
        result.test_env.site_packages.joinpath("project.egg-link")
        in result.files_created
    ), ".egg-link file should have been created"


def test_wheel_editable_pep660_basic(tmpdir: Path, script: PipTestEnvironment) -> None:
    """
    Test 'pip wheel' of an editable pep 660 project.
    It must *not* call prepare_metadata_for_build_editable.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITH_PEP660, with_setup_py=False)
    wheel_dir = tmpdir / "dist"
    script.pip(
        "wheel",
        "--no-index",
        "--no-build-isolation",
        "--editable",
        project_dir,
        "-w",
        wheel_dir,
    )
    _assert_hook_not_called(project_dir, "prepare_metadata_for_build_editable")
    _assert_hook_not_called(project_dir, "build_editable")
    _assert_hook_called(project_dir, "prepare_metadata_for_build_wheel")
    _assert_hook_called(project_dir, "build_wheel")
    assert len(os.listdir(str(wheel_dir))) == 1, "a wheel should have been created"


def test_download_editable_pep660_basic(
    tmpdir: Path, script: PipTestEnvironment
) -> None:
    """
    Test 'pip download' of an editable pep 660 project.
    It must *not* call prepare_metadata_for_build_editable.
    """
    project_dir = _make_project(tmpdir, BACKEND_WITH_PEP660, with_setup_py=False)
    reqs_file = tmpdir / "requirements.txt"
    reqs_file.write_text(f"-e {project_dir.as_uri()}\n")
    download_dir = tmpdir / "download"
    script.pip(
        "download",
        "--no-index",
        "--no-build-isolation",
        "-r",
        reqs_file,
        "-d",
        download_dir,
    )
    _assert_hook_not_called(project_dir, "prepare_metadata_for_build_editable")
    _assert_hook_called(project_dir, "prepare_metadata_for_build_wheel")
    assert len(os.listdir(str(download_dir))) == 1, "a zip should have been created"
