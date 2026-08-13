import json
from pathlib import Path
from typing import Any

import pytest
from packaging.utils import canonicalize_name

from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME

from tests.lib import PipTestEnvironment, ScriptFactory, TestData


@pytest.fixture
def simple_script(
    tmpdir_factory: pytest.TempPathFactory,
    script_factory: ScriptFactory,
    shared_data: TestData,
) -> PipTestEnvironment:
    tmpdir = tmpdir_factory.mktemp("pip_test_package")
    script = script_factory(tmpdir.joinpath("workspace"))
    script.pip(
        "install",
        "-f",
        shared_data.find_links,
        "--no-index",
        "simplewheel==1.0",
    )
    return script


def _make_project(path: Path, *, name: str, version: str = "1.0") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    path.joinpath("pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n'
    )
    package_dir = path / canonicalize_name(name).replace("-", "_")
    package_dir.mkdir(exist_ok=True)
    package_dir.joinpath("__init__.py").write_text("")
    return path


def _inspect_entry(script: PipTestEnvironment, name: str, **kwargs: Any) -> Any:
    result = script.pip("inspect", **kwargs)
    assert "Traceback" not in result.stderr
    data = json.loads(result.stdout)
    for entry in data["installed"]:
        if canonicalize_name(entry["metadata"]["name"]) == canonicalize_name(name):
            return entry
    return None


def test_inspect_basic(simple_script: PipTestEnvironment) -> None:
    """
    Test default behavior of inspect command.
    """
    result = simple_script.pip("inspect")
    report = json.loads(result.stdout)
    installed_by_name = {i["metadata"]["name"]: i for i in report["installed"]}
    # Coverage is only installed if test coverage is being collected.
    installed_by_name.pop("coverage", None)
    assert len(installed_by_name) == 3
    assert installed_by_name.keys() == {
        "pip",
        "setuptools",
        "simplewheel",
    }
    assert installed_by_name["simplewheel"]["metadata"]["version"] == "1.0"
    assert installed_by_name["simplewheel"]["requested"] is True
    assert installed_by_name["simplewheel"]["installer"] == "pip"
    assert "environment" in report


@pytest.mark.parametrize("editable", [False, True], ids=["not-editable", "editable"])
def test_inspect_direct_url_local_directory(
    script: PipTestEnvironment, tmp_path: Path, editable: bool
) -> None:
    """``pip inspect`` serializes ``direct_url`` for a local directory install
    exactly as pip recorded it in ``direct_url.json`` (same shape for a normal
    and a PEP 660 editable install; editable state lives in dir_info.editable)."""
    project_path = _make_project(tmp_path / "pkga", name="pkga")
    args = ["install", "--no-build-isolation", "--no-index"]
    if editable:
        args.append("--editable")
    args.append(str(project_path))
    result = script.pip(*args)
    recorded = result.get_created_direct_url("pkga")
    assert recorded is not None

    entry = _inspect_entry(script, "pkga")
    assert entry is not None
    assert entry["direct_url"] == recorded.to_dict_compat()
    assert entry["direct_url"]["url"].endswith("/pkga")
    assert entry["direct_url"]["dir_info"] == ({"editable": True} if editable else {})
    assert "subdirectory" not in entry["direct_url"]
    assert entry["metadata_location"]


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("[]", id="json-array"),
        pytest.param("not a json document", id="not-json"),
        pytest.param('{"url": 1}', id="wrong-value-type"),
    ],
)
def test_inspect_malformed_direct_url(
    script: PipTestEnvironment, tmp_path: Path, content: str
) -> None:
    """A missing/malformed ``direct_url.json`` must not make ``pip inspect``
    crash, and pip must not invent a more specific origin than it knows: the
    entry simply carries no ``direct_url``."""
    project_path = _make_project(tmp_path / "pkga", name="pkga")
    result = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        str(project_path),
    )
    direct_url_path = result.get_created_direct_url_path("pkga")
    assert direct_url_path and direct_url_path.name == DIRECT_URL_METADATA_NAME
    direct_url_path.write_text(content)

    entry = _inspect_entry(script, "pkga", allow_stderr_warning=True)
    assert entry is not None
    assert "direct_url" not in entry


def test_inspect_no_direct_url(
    script: PipTestEnvironment, shared_data: TestData
) -> None:
    """A package installed from an index/find-links has no ``direct_url.json``;
    ``pip inspect`` reports it without a ``direct_url`` (no invented origin)."""
    script.pip(
        "install",
        "--no-index",
        "-f",
        shared_data.find_links,
        "simplewheel==1.0",
    )
    entry = _inspect_entry(script, "simplewheel")
    assert entry is not None
    assert "direct_url" not in entry
