import json
import tarfile
from pathlib import Path
from typing import List, Optional, Tuple
from zipfile import ZipFile

from pip._internal.utils.urls import path_to_url

from tests.lib import PipTestEnvironment, create_basic_sdist_for_package

PYPROJECT_TOML = """\
[build-system]
requires = []
build-backend = "dummy_backend:main"
backend-path = ["backend"]
"""

BACKEND_SRC = '''
import csv
import json
import os.path
from zipfile import ZipFile
import hashlib
import base64
import io

WHEEL = """\
Wheel-Version: 1.0
Generator: dummy_backend 1.0
Root-Is-Purelib: true
Tag: py3-none-any
"""

METADATA = """\
Metadata-Version: 2.1
Name: {project}
Version: {version}
Summary: A dummy package
Author: None
Author-email: none@example.org
License: MIT
{requires_dist}
"""

def make_wheel(z, project, version, requires_dist, files):
    record = []
    def add_file(name, data):
        data = data.encode("utf-8")
        z.writestr(name, data)
        digest = hashlib.sha256(data).digest()
        hash = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ASCII")
        record.append((name, f"sha256={hash}", len(data)))
    distinfo = f"{project}-{version}.dist-info"
    add_file(f"{distinfo}/WHEEL", WHEEL)
    add_file(f"{distinfo}/METADATA", METADATA.format(
        project=project, version=version, requires_dist=requires_dist
    ))
    for name, data in files:
        add_file(name, data)
    record_name = f"{distinfo}/RECORD"
    record.append((record_name, "", ""))
    b = io.BytesIO()
    rec = io.TextIOWrapper(b, newline="", encoding="utf-8")
    w = csv.writer(rec)
    w.writerows(record)
    z.writestr(record_name, b.getvalue())
    rec.close()


class Backend:
    def build_wheel(
        self,
        wheel_directory,
        config_settings=None,
        metadata_directory=None
    ):
        if config_settings is None:
            config_settings = {}
        w = os.path.join(wheel_directory, "{{name}}-1.0-py3-none-any.whl")
        with open(w, "wb") as f:
            with ZipFile(f, "w") as z:
                make_wheel(
                    z, "{{name}}", "1.0", "{{requires_dist}}",
                    [("{{name}}-config.json", json.dumps(config_settings))]
                )
        return "{{name}}-1.0-py3-none-any.whl"

    build_editable = build_wheel

main = Backend()
'''


def make_project(
    path: Path, name: str = "foo", dependencies: Optional[List[str]] = None
) -> Tuple[str, str, Path]:
    version = "1.0"
    project_dir = path / name
    backend = project_dir / "backend"
    backend.mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(PYPROJECT_TOML)
    requires_dist = [f"Requires-Dist: {dep}" for dep in dependencies or []]
    (backend / "dummy_backend.py").write_text(
        BACKEND_SRC.replace("{{name}}", name).replace(
            "{{requires_dist}}", "\n".join(requires_dist)
        )
    )
    return name, version, project_dir


def test_config_settings_implies_pep517(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    """Test that setup.py bdist_wheel is not used when config settings are."""
    pkg_path = tmp_path / "pkga"
    pkg_path.mkdir()
    pkg_path.joinpath("setup.py").write_text(
        "from setuptools import setup; setup(name='pkga')\n"
    )
    result = script.pip(
        "wheel",
        "--no-build-isolation",
        "--config-settings",
        "FOO=Hello",
        pkg_path,
        cwd=tmp_path,
    )
    assert "Successfully built pkga" in result.stdout
    assert "Preparing metadata (pyproject.toml)" in result.stdout


def test_backend_sees_config(script: PipTestEnvironment) -> None:
    name, version, project_dir = make_project(script.scratch_path)
    script.pip(
        "wheel",
        "--config-settings",
        "FOO=Hello",
        project_dir,
    )
    wheel_file_name = f"{name}-{version}-py3-none-any.whl"
    wheel_file_path = script.cwd / wheel_file_name
    with open(wheel_file_path, "rb") as f:
        with ZipFile(f) as z:
            output = z.read(f"{name}-config.json")
            assert json.loads(output) == {"FOO": "Hello"}


def test_backend_sees_config_reqs(script: PipTestEnvironment) -> None:
    name, version, project_dir = make_project(script.scratch_path)
    script.scratch_path.joinpath("reqs.txt").write_text(
        f"{project_dir} --config-settings FOO=Hello"
    )
    script.pip("wheel", "-r", "reqs.txt")
    wheel_file_name = f"{name}-{version}-py3-none-any.whl"
    wheel_file_path = script.cwd / wheel_file_name
    with open(wheel_file_path, "rb") as f:
        with ZipFile(f) as z:
            output = z.read(f"{name}-config.json")
            assert json.loads(output) == {"FOO": "Hello"}


def test_backend_sees_config_via_constraint(script: PipTestEnvironment) -> None:
    name, version, project_dir = make_project(script.scratch_path)
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"{name} @ {path_to_url(str(project_dir))}")
    script.pip(
        "wheel",
        "--config-settings",
        "FOO=Hello",
        "-c",
        "constraints.txt",
        name,
    )
    wheel_file_name = f"{name}-{version}-py3-none-any.whl"
    wheel_file_path = script.cwd / wheel_file_name
    with open(wheel_file_path, "rb") as f:
        with ZipFile(f) as z:
            output = z.read(f"{name}-config.json")
            assert json.loads(output) == {"FOO": "Hello"}


def test_backend_sees_config_via_sdist(script: PipTestEnvironment) -> None:
    name, version, project_dir = make_project(script.scratch_path)
    dists_dir = script.scratch_path / "dists"
    dists_dir.mkdir()
    with tarfile.open(dists_dir / f"{name}-{version}.tar.gz", "w:gz") as dist_tar:
        dist_tar.add(project_dir, arcname=name)
    script.pip(
        "wheel",
        "--config-settings",
        "FOO=Hello",
        "-f",
        dists_dir,
        name,
    )
    wheel_file_name = f"{name}-{version}-py3-none-any.whl"
    wheel_file_path = script.cwd / wheel_file_name
    with open(wheel_file_path, "rb") as f:
        with ZipFile(f) as z:
            output = z.read(f"{name}-config.json")
            assert json.loads(output) == {"FOO": "Hello"}


def test_req_file_does_not_see_config(script: PipTestEnvironment) -> None:
    """Test that CLI config settings do not propagate to requirement files."""
    name, _, project_dir = make_project(script.scratch_path)
    reqs_file = script.scratch_path / "reqs.txt"
    reqs_file.write_text(f"{project_dir}")
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        "-r",
        reqs_file,
    )
    config = script.site_packages_path / f"{name}-config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {}


def test_dep_does_not_see_config(script: PipTestEnvironment) -> None:
    """Test that CLI config settings do not propagate to dependencies."""
    _, _, bar_project_dir = make_project(script.scratch_path, name="bar")
    _, _, foo_project_dir = make_project(
        script.scratch_path,
        name="foo",
        dependencies=[f"bar @ {path_to_url(str(bar_project_dir))}"],
    )
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        foo_project_dir,
    )
    foo_config = script.site_packages_path / "foo-config.json"
    with open(foo_config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}
    bar_config = script.site_packages_path / "bar-config.json"
    with open(bar_config, "rb") as f:
        assert json.load(f) == {}


def test_dep_in_req_file_does_not_see_config(script: PipTestEnvironment) -> None:
    """Test that CLI config settings do not propagate to dependencies found in
    requirement files."""
    _, _, bar_project_dir = make_project(script.scratch_path, name="bar")
    _, _, foo_project_dir = make_project(
        script.scratch_path,
        name="foo",
        dependencies=["bar"],
    )
    reqs_file = script.scratch_path / "reqs.txt"
    reqs_file.write_text(f"bar @ {path_to_url(str(bar_project_dir))}")
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        "-r",
        reqs_file,
        foo_project_dir,
    )
    foo_config = script.site_packages_path / "foo-config.json"
    with open(foo_config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}
    bar_config = script.site_packages_path / "bar-config.json"
    with open(bar_config, "rb") as f:
        assert json.load(f) == {}


def test_install_sees_config(script: PipTestEnvironment) -> None:
    name, _, project_dir = make_project(script.scratch_path)
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        project_dir,
    )
    config = script.site_packages_path / f"{name}-config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}


def test_install_sees_config_reqs(script: PipTestEnvironment) -> None:
    name, _, project_dir = make_project(script.scratch_path)
    script.scratch_path.joinpath("reqs.txt").write_text(
        f"{project_dir} --config-settings FOO=Hello"
    )
    script.pip("install", "-r", "reqs.txt")
    config = script.site_packages_path / f"{name}-config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}


def test_install_editable_sees_config(script: PipTestEnvironment) -> None:
    name, _, project_dir = make_project(script.scratch_path)
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        "--editable",
        project_dir,
    )
    config = script.site_packages_path / f"{name}-config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}


def test_install_config_reqs(script: PipTestEnvironment) -> None:
    name, _, project_dir = make_project(script.scratch_path)
    a_sdist = create_basic_sdist_for_package(
        script,
        "foo",
        "1.0",
        {"pyproject.toml": PYPROJECT_TOML, "backend/dummy_backend.py": BACKEND_SRC},
    )
    script.scratch_path.joinpath("reqs.txt").write_text(
        f'{project_dir} --config-settings "--build-option=--cffi" '
        '--config-settings "--build-option=--avx2" '
        "--config-settings FOO=BAR"
    )
    script.pip("install", "--no-index", "-f", str(a_sdist.parent), "-r", "reqs.txt")
    script.assert_installed(foo="1.0")
    config = script.site_packages_path / f"{name}-config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"--build-option": ["--cffi", "--avx2"], "FOO": "BAR"}
