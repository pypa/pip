# Copyright 2017 Alethea Katherine Flowers
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

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
from typing import TYPE_CHECKING, Sequence, TypeVar

from colorlog.escape_codes import parse_colors

import nox
from nox import _options, registry
from nox._resolver import CycleError
from nox._version import InvalidVersionSpecifier, VersionCheckFailed, check_nox_version
from nox.logger import logger
from nox.manifest import WARN_PYTHONS_IGNORED, Manifest
from nox.sessions import Result, Status

if TYPE_CHECKING:
    import types
    from argparse import Namespace

__all__ = [
    "create_report",
    "discover_manifest",
    "filter_manifest",
    "final_reduce",
    "honor_list_request",
    "load_nox_module",
    "merge_noxfile_options",
    "print_summary",
    "run_manifest",
]


def __dir__() -> list[str]:
    return __all__


def _load_and_exec_nox_module(global_config: Namespace) -> types.ModuleType:
    """
    Loads, executes, then returns the global_config Nox module.

    Args:
        global_config (Namespace): The global config.

    Raises:
        IOError: If the Nox module cannot be loaded. This
            exception is chosen such that it will be caught
            by load_nox_module and logged appropriately.

    Returns:
        types.ModuleType: The initialised Nox module.
    """
    spec = importlib.util.spec_from_file_location(
        "user_nox_module", global_config.noxfile
    )
    assert spec is not None  # If None, fatal importlib error, would crash anyway

    module = importlib.util.module_from_spec(spec)
    assert module is not None  # If None, fatal importlib error, would crash anyway

    sys.modules["user_nox_module"] = module

    loader = spec.loader
    assert loader is not None  # If None, fatal importlib error, would crash anyway
    # See https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    loader.exec_module(module)
    return module


def load_nox_module(global_config: Namespace) -> types.ModuleType | int:
    """Load the user's Noxfile and return the module object for it.

    .. note::

        This task has two side effects; it makes ``global_config.noxfile``
        an absolute path, and changes the working directory of the process.

    Args:
        global_config (.nox.main.GlobalConfig): The global config.

    Returns:
        module: The module designated by the Noxfile path.
    """
    # Be sure to expand variables
    global_config_noxfile = os.path.expandvars(global_config.noxfile)

    # Make sure we only expand the parent dir just in case the noxfile is a symlink
    noxfile_parent_dir = os.path.realpath(os.path.dirname(global_config_noxfile))

    # Save the absolute path to the Noxfile.
    # This will inoculate it if Nox changes paths because of an implicit
    # or explicit chdir (like the one below).
    global_config.noxfile = os.path.join(
        noxfile_parent_dir, os.path.basename(global_config_noxfile)
    )

    try:
        # Check ``nox.needs_version`` by parsing the AST.
        check_nox_version(global_config.noxfile)

        # Move to the path where the Noxfile is.
        # This will ensure that the Noxfile's path is on sys.path, and that
        # import-time path resolutions work the way the Noxfile author would
        # guess. The original working directory (the directory that Nox was
        # invoked from) gets stored by the .invoke_from "option" in _options.
        os.chdir(noxfile_parent_dir)

    except (VersionCheckFailed, InvalidVersionSpecifier) as error:
        logger.error(str(error))
        return 2
    except FileNotFoundError:
        logger.error(
            f"Failed to load Noxfile {global_config.noxfile}, no such file exists."
        )
        return 2
    except OSError:
        logger.exception(f"Failed to load Noxfile {global_config.noxfile}")
        return 2

    return _load_and_exec_nox_module(global_config)


def merge_noxfile_options(
    module: types.ModuleType, global_config: Namespace
) -> types.ModuleType:
    """Merges any modifications made to ``nox.options`` by the Noxfile module
    into global_config.

    Args:
        module (module): The Noxfile module.
        global_config (~nox.main.GlobalConfig): The global configuration.
    """
    _options.options.merge_namespaces(global_config, nox.options)
    return module


def discover_manifest(
    module: types.ModuleType | int, global_config: Namespace
) -> Manifest:
    """Discover all session functions in the Noxfile module.

    Args:
        module (module): The Noxfile module.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        ~.Manifest: A manifest of session functions.
    """
    # Find any function added to the session registry (meaning it was
    # decorated with @nox.session); do not sort these, as they are being
    # sorted by decorator call time.
    functions = registry.get()

    # Get the docstring from the Noxfile
    module_docstring = module.__doc__

    # Return the final dictionary of session functions.
    return Manifest(functions, global_config, module_docstring)


def filter_manifest(manifest: Manifest, global_config: Namespace) -> Manifest | int:
    """Filter the manifest according to the provided configuration.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        Union[~.Manifest,int]: ``3`` if a specified session is not found,
            the manifest otherwise (to be sent to the next task).

    """
    # Shouldn't happen unless the Noxfile is empty
    if not manifest:
        logger.error(f"No sessions found in {global_config.noxfile}.")
        return 3

    # Filter by the name of any explicit sessions.
    # This can raise KeyError if a specified session does not exist;
    # log this if it happens. The sessions does not come from the Noxfile
    # if keywords is not empty.
    if global_config.sessions is None:
        manifest.filter_by_default()
    else:
        try:
            manifest.filter_by_name(global_config.sessions)
        except KeyError as exc:
            logger.error("Error while collecting sessions.")
            logger.error(exc.args[0])
            return 3

    if not manifest and not global_config.list_sessions:
        print("No sessions selected. Please select a session with -s <session name>.\n")
        _produce_listing(manifest, global_config)
        return 0

    # Filter by python interpreter versions.
    if global_config.pythons:
        manifest.filter_by_python_interpreter(global_config.pythons)
        if not manifest and not global_config.list_sessions:
            logger.error("Python version selection caused no sessions to be selected.")
            return 3

    # Filter by tags.
    if global_config.tags is not None:
        manifest.filter_by_tags(global_config.tags)
        if not manifest and not global_config.list_sessions:
            logger.error("Tag selection caused no sessions to be selected.")
            return 3

    # Filter by keywords.
    if global_config.keywords:
        try:
            ast.parse(global_config.keywords, mode="eval")
        except SyntaxError:
            logger.error(
                "Error while collecting sessions: keywords argument must be a Python"
                " expression."
            )
            return 3

        # This function never errors, but may cause an empty list of sessions
        # (which is an error condition later).
        manifest.filter_by_keywords(global_config.keywords)

    if not manifest and not global_config.list_sessions:
        logger.error("No sessions selected after filtering by keyword.")
        return 3

    # Add dependencies.
    try:
        manifest.add_dependencies()
    except (KeyError, CycleError) as exc:
        logger.error("Error while resolving session dependencies.")
        logger.error(exc.args[0])
        return 3

    # Return the modified manifest.
    return manifest


def _produce_listing(manifest: Manifest, global_config: Namespace) -> None:
    # If the user just asked for a list of sessions, print that
    # and any docstring specified in noxfile.py and be done. This
    # can also be called if Noxfile sessions is an empty list.

    if manifest.module_docstring:
        print(manifest.module_docstring.strip(), end="\n\n")

    print(f"Sessions defined in {global_config.noxfile}:\n")

    reset = parse_colors("reset") if global_config.color else ""
    selected_color = parse_colors("cyan") if global_config.color else ""
    skipped_color = parse_colors("white") if global_config.color else ""

    for session, selected in manifest.list_all_sessions():
        output = "{marker} {color}{session}{reset}"

        if selected:
            marker = "*"
            color = selected_color
        else:
            marker = "-"
            color = skipped_color

        if session.description is not None:
            output += " -> {description}"

        print(
            output.format(
                color=color,
                reset=reset,
                session=session.friendly_name,
                description=session.description,
                marker=marker,
            )
        )

    print(
        f"\nsessions marked with {selected_color}*{reset} are selected, sessions marked"
        f" with {skipped_color}-{reset} are skipped."
    )


def _produce_json_listing(manifest: Manifest, global_config: Namespace) -> None:  # noqa: ARG001
    report = []
    for session, selected in manifest.list_all_sessions():
        if selected:
            report.append(
                {
                    "session": session.friendly_name,
                    "name": session.name,
                    "description": session.description or "",
                    "python": session.func.python,
                    "tags": session.tags,
                    "call_spec": getattr(session.func, "call_spec", {}),
                }
            )
    print(json.dumps(report))


def honor_list_request(manifest: Manifest, global_config: Namespace) -> Manifest | int:
    """If --list was passed, simply list the manifest and exit cleanly.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        Union[~.Manifest,int]: ``0`` if a listing is all that is requested,
            the manifest otherwise (to be sent to the next task).
    """
    if not (global_config.list_sessions or global_config.json):
        return manifest

    # JSON output requires list sessions also be specified
    if global_config.json and not global_config.list_sessions:
        logger.error("Must specify --list-sessions with --json")
        return 3

    if global_config.json:
        _produce_json_listing(manifest, global_config)
    else:
        _produce_listing(manifest, global_config)

    return 0


def run_manifest(manifest: Manifest, global_config: Namespace) -> list[Result]:
    """Run the full manifest of sessions.

    Args:
        manifest (~.Manifest): The manifest of sessions to be run.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        tuple[~nox.sessions.Session,~.SessionStatus]: A two-tuple of the
            sessions and the result of each session that was run.
    """
    results = []

    # Iterate over each session in the manifest, and execute it.
    #
    # Note that it is possible for the manifest to be altered in any given
    # iteration.
    for session in manifest:
        # possibly raise warnings associated with this session
        if WARN_PYTHONS_IGNORED in session.func.should_warn:
            logger.warning(
                f"Session {session.name} is set to run with venv_backend='none', "
                "IGNORING its"
                f" python={session.func.should_warn[WARN_PYTHONS_IGNORED]} parametrization. "
            )

        result = session.execute()
        name = session.friendly_name
        status = result.imperfect
        result.log(f"Session {name} {status}.")
        results.append(result)

        # Sanity check: If we are supposed to stop on the first error case,
        # the abort now.
        if not result and global_config.stop_on_first_error:
            return results

    # The entire manifest has been processed; return the results.
    return results


Sequence_Results_T = TypeVar("Sequence_Results_T", bound=Sequence[Result])


def print_summary(
    results: Sequence_Results_T,
    global_config: Namespace,  # noqa: ARG001
) -> Sequence_Results_T:
    """Print a summary of the results.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects.
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        results (Sequence[~nox.sessions.Result]): The results passed
            to this function, unmodified.
    """
    # Sanity check: Do not print results if there was only one session run.
    if len(results) <= 1:
        return results

    # Iterate over the results and print the result for each in a
    # human-readable way.
    logger.warning("Ran multiple sessions:")
    for result in results:
        name = result.session.friendly_name
        status = result.status.name.lower()
        if result.status is Status.SKIPPED and result.reason:
            result.log(f"* {name}: {status} ({result.reason})")
        else:
            result.log(f"* {name}: {status}")

    # Return the results that were sent to this function.
    return results


def create_report(
    results: Sequence_Results_T, global_config: Namespace
) -> Sequence_Results_T:
    """Write a report to the location designated in the config, if any.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        results (Sequence[~nox.sessions.Result]): The results passed
            to this function, unmodified.
    """
    # Sanity check: If no JSON report was requested, this is a no-op.
    if global_config.report is None:
        return results

    # Write the JSON report.
    with open(global_config.report, "w", encoding="utf-8") as report_file:
        json.dump(
            {
                "result": int(all(results)),
                "sessions": [result.serialize() for result in results],
            },
            report_file,
            indent=2,
        )

    # Return back the results passed to this task.
    return results


def final_reduce(results: list[Result], global_config: Namespace) -> int:  # noqa: ARG001
    """Reduce the results to a final exit code.

    Args:
        results (Sequence[~nox.sessions.Result]): A list of Result objects
        global_config (~nox.main.GlobalConfig): The global configuration.

    Returns:
        int: The final status code; ``0`` for success and ``1`` for failure.
    """
    if not all(results):
        return 1
    return 0
