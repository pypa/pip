# Copyright 2016 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The Nox `main` function and helpers."""

from __future__ import annotations

import importlib.metadata
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import packaging.requirements
import packaging.utils

import nox.command
import nox.virtualenv
from nox import _options, tasks, workflow
from nox._version import get_nox_version
from nox.logger import setup_logging
from nox.project import load_toml

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["execute_workflow", "main"]


def __dir__() -> list[str]:
    return __all__


def execute_workflow(args: Any) -> int:
    """
    Execute the appropriate tasks.
    """

    return workflow.execute(
        global_config=args,
        workflow=(
            tasks.load_nox_module,
            tasks.merge_noxfile_options,
            tasks.discover_manifest,
            tasks.filter_manifest,
            tasks.honor_list_request,
            tasks.run_manifest,
            tasks.print_summary,
            tasks.create_report,
            tasks.final_reduce,
        ),
    )


def get_dependencies(
    req: packaging.requirements.Requirement,
) -> Generator[packaging.requirements.Requirement, None, None]:
    """
    Gets all dependencies. Raises ModuleNotFoundError if a package is not installed.
    """
    info = importlib.metadata.metadata(req.name)
    yield req

    dist_list = info.get_all("requires-dist") or []
    extra_list = [packaging.requirements.Requirement(mk) for mk in dist_list]
    for extra in req.extras:
        for ireq in extra_list:
            if ireq.marker and not ireq.marker.evaluate({"extra": extra}):
                continue
            yield from get_dependencies(ireq)


def check_dependencies(dependencies: list[str]) -> bool:
    """
    Checks to see if a list of dependencies is currently installed.
    """
    itr_deps = (packaging.requirements.Requirement(d) for d in dependencies)
    deps = [d for d in itr_deps if not d.marker or d.marker.evaluate()]

    # Select the one nox dependency (required)
    nox_dep = [d for d in deps if packaging.utils.canonicalize_name(d.name) == "nox"]
    if not nox_dep:
        msg = "Must have a nox dependency in TOML script dependencies"
        raise ValueError(msg)

    try:
        expanded_deps = {d for req in deps for d in get_dependencies(req)}
    except ModuleNotFoundError:
        return False

    for dep in expanded_deps:
        if dep.specifier:
            version = importlib.metadata.version(dep.name)
            if not dep.specifier.contains(version):
                return False
        if dep.url:
            dist = importlib.metadata.distribution(dep.name)
            if not check_url_dependency(dep.url, dist):
                return False

    return True


def check_url_dependency(dep_url: str, dist: importlib.metadata.Distribution) -> bool:
    """
    Check to see if a url matches an installed distribution object. Returns false if
    this is not a clear match.
    """

    # The .origin property added in Python 3.13
    origin = getattr(dist, "origin", None)
    if origin is None:
        return False

    dep_purl = urllib.parse.urlparse(dep_url)

    if hasattr(origin, "requested_revision"):
        origin_purl = urllib.parse.urlparse(f"{origin.url}@{origin.requested_revision}")
    else:
        origin_purl = urllib.parse.urlparse(origin.url)

    return dep_purl.netloc == origin_purl.netloc and dep_purl.path == origin_purl.path


def run_script_mode(
    envdir: Path, *, reuse: bool, dependencies: list[str], venv_backend: str
) -> NoReturn:
    envdir.mkdir(exist_ok=True)
    noxenv = envdir.joinpath("_nox_script_mode")
    venv = nox.virtualenv.get_virtualenv(
        *venv_backend.split("|"),
        reuse_existing=reuse,
        envdir=str(noxenv),
    )
    venv.create()
    env = {k: v for k, v in venv._get_env({}).items() if v is not None}
    env["NOX_SCRIPT_MODE"] = "none"
    cmd = (
        [nox.virtualenv.UV, "pip", "install"]
        if venv.venv_backend == "uv"
        else ["pip", "install"]
    )
    subprocess.run([*cmd, *dependencies], env=env, check=True)
    nox_cmd = shutil.which("nox", path=env["PATH"])
    assert nox_cmd is not None, "Nox must be discoverable when installed"
    # The os.exec functions don't work properly on Windows
    if sys.platform.startswith("win"):
        raise SystemExit(
            subprocess.run(
                [nox_cmd, *sys.argv[1:]],
                env=env,
                stdout=None,
                stderr=None,
                encoding="utf-8",
                text=True,
                check=False,
            ).returncode
        )
    os.execle(nox_cmd, nox_cmd, *sys.argv[1:], env)  # pragma: nocover # noqa: S606


def main() -> None:
    args = _options.options.parse_args()

    if args.help:
        _options.options.print_help()
        return

    if args.version:
        print(get_nox_version(), file=sys.stderr)
        return

    setup_logging(
        color=args.color, verbose=args.verbose, add_timestamp=args.add_timestamp
    )
    nox_script_mode = os.environ.get("NOX_SCRIPT_MODE", "") or args.script_mode
    if nox_script_mode not in {"none", "reuse", "fresh"}:
        msg = f"Invalid NOX_SCRIPT_MODE: {nox_script_mode!r}, must be one of 'none', 'reuse', or 'fresh'"
        raise SystemExit(msg)
    if nox_script_mode != "none":
        toml_config = load_toml(os.path.expandvars(args.noxfile), missing_ok=True)
        dependencies = toml_config.get("dependencies")
        if dependencies is not None:
            valid_env = check_dependencies(dependencies)
            # Coverage misses this, but it's covered via subprocess call
            if not valid_env:  # pragma: nocover
                venv_backend = (
                    os.environ.get("NOX_SCRIPT_VENV_BACKEND")
                    or args.script_venv_backend
                    or (
                        toml_config.get("tool", {})
                        .get("nox", {})
                        .get("script-venv-backend", "uv|virtualenv")
                    )
                )

                envdir = Path(args.envdir or ".nox")
                run_script_mode(
                    envdir,
                    reuse=nox_script_mode == "reuse",
                    dependencies=dependencies,
                    venv_backend=venv_backend,
                )

    exit_code = execute_workflow(args)

    # Done; exit.
    sys.exit(exit_code)
