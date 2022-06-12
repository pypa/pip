import json
from pathlib import Path
from typing import Tuple
from zipfile import ZipFile

from tests.lib import PipTestEnvironment

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
"""

def make_wheel(z, project, version, files):
    record = []
    def add_file(name, data):
        data = data.encode("utf-8")
        z.writestr(name, data)
        digest = hashlib.sha256(data).digest()
        hash = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ASCII")
        record.append((name, f"sha256={hash}", len(data)))
    distinfo = f"{project}-{version}.dist-info"
    add_file(f"{distinfo}/WHEEL", WHEEL)
    add_file(f"{distinfo}/METADATA", METADATA.format(project=project, version=version))
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
        w = os.path.join(wheel_directory, "foo-1.0-py3-none-any.whl")
        with open(w, "wb") as f:
            with ZipFile(f, "w") as z:
                make_wheel(
                    z, "foo", "1.0",
                    [("config.json", json.dumps(config_settings))]
                )
        return "foo-1.0-py3-none-any.whl"

    build_editable = build_wheel

main = Backend()
'''


def make_project(path: Path) -> Tuple[str, str, Path]:
    name = "foo"
    version = "1.0"
    project_dir = path / name
    backend = project_dir / "backend"
    backend.mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(PYPROJECT_TOML)
    (backend / "dummy_backend.py").write_text(BACKEND_SRC)
    return name, version, project_dir


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
            output = z.read("config.json")
            assert json.loads(output) == {"FOO": "Hello"}


def test_install_sees_config(script: PipTestEnvironment) -> None:
    _, _, project_dir = make_project(script.scratch_path)
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        project_dir,
    )
    config = script.site_packages_path / "config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}


def test_install_editable_sees_config(script: PipTestEnvironment) -> None:
    _, _, project_dir = make_project(script.scratch_path)
    script.pip(
        "install",
        "--config-settings",
        "FOO=Hello",
        "--editable",
        project_dir,
    )
    config = script.site_packages_path / "config.json"
    with open(config, "rb") as f:
        assert json.load(f) == {"FOO": "Hello"}
