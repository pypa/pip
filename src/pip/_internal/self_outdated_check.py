import datetime
import hashlib
import json
import logging
import optparse
import os.path
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from pip._vendor.packaging.version import parse as parse_version

from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import get_default_environment
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.network.session import PipSession
from pip._internal.utils.filesystem import adjacent_tmp_file, check_path_owner, replace
from pip._internal.utils.misc import ensure_dir

SELFCHECK_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


logger = logging.getLogger(__name__)


def _get_statefile_name(key: str) -> str:
    key_bytes = key.encode()
    name = hashlib.sha224(key_bytes).hexdigest()
    return name


class SelfCheckState:
    def __init__(self, cache_dir: str) -> None:
        self.state: Dict[str, Any] = {}
        self.statefile_path = None

        # Try to load the existing state
        if cache_dir:
            self.statefile_path = os.path.join(
                cache_dir, "selfcheck", _get_statefile_name(self.key)
            )
            try:
                with open(self.statefile_path, encoding="utf-8") as statefile:
                    self.state = json.load(statefile)
            except (OSError, ValueError, KeyError):
                # Explicitly suppressing exceptions, since we don't want to
                # error out if the cache file is invalid.
                pass

    @property
    def key(self) -> str:
        return sys.prefix

    def save(self, pypi_version: str, current_time: datetime.datetime) -> None:
        # If we do not have a path to cache in, don't bother saving.
        if not self.statefile_path:
            return

        # Check to make sure that we own the directory
        if not check_path_owner(os.path.dirname(self.statefile_path)):
            return

        # Now that we've ensured the directory is owned by this user, we'll go
        # ahead and make sure that all our directories are created.
        ensure_dir(os.path.dirname(self.statefile_path))

        state = {
            # Include the key so it's easy to tell which pip wrote the
            # file.
            "key": self.key,
            "last_check": current_time.strftime(SELFCHECK_DATE_FMT),
            "pypi_version": pypi_version,
        }

        text = json.dumps(state, sort_keys=True, separators=(",", ":"))

        with adjacent_tmp_file(self.statefile_path) as f:
            f.write(text.encode())

        try:
            # Since we have a prefix-specific state file, we can just
            # overwrite whatever is there, no need to check.
            replace(f.name, self.statefile_path)
        except OSError:
            # Best effort.
            pass


def was_installed_by_pip(pkg: str) -> bool:
    """Checks whether pkg was installed by pip

    This is used not to display the upgrade message when pip is in fact
    installed by system package manager, such as dnf on Fedora.
    """
    dist = get_default_environment().get_distribution(pkg)
    return dist is not None and "pip" == dist.installer


def get_py_executable() -> str:
    """Get path to launch a Python executable.

    First test if python/python3/pythonX.Y on PATH matches the current
    interpreter, and use that if possible. Then try to get the correct
    pylauncher command to launch a process of the current python
    version, fallback to sys.executable
    """

    if not sys.executable:
        # docs (python 3.10) says that sys.executable can be can be None or an
        # empty string if this value cannot be determined, although this is
        # very rare. In this case, there is nothing much we can do
        return "python3"

    # windows paths are case-insensitive, pathlib takes that into account
    sys_executable_path = Path(sys.executable)

    major, minor, *_ = sys.version_info

    # first handle common case: test if path to python/python3/pythonX.Y
    # matches sys.executable
    for py in ("python", "python3", f"python{major}.{minor}"):
        which = shutil.which(py)
        if which is None:
            continue

        try:
            # resolve() removes symlinks, normalises paths and makes them
            # absolute
            if Path(which).resolve() == sys_executable_path.resolve():
                return py

        except RuntimeError:
            # happens when resolve() encounters an infinite loop
            pass

    # version in the format used by pylauncher
    pylauncher_version = f"-{major}.{minor}-{64 if sys.maxsize > 2**32 else 32}"

    # checks that pylauncher is usable, also makes sure pylauncher recognises
    # the current python version and has the correct path of the current
    # executable.
    try:
        proc = subprocess.run(
            ["py", "--list-paths"],
            capture_output=True,
            timeout=1,
            text=True,
            check=True,
        )

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        pass

    else:
        for line in proc.stdout.splitlines():
            # this is not failsafe, in the future pylauncher might change
            # the format of the output. In that case, this implementation
            # would start falling back to sys.executable which is better than
            # throwing unhandled exceptions to users
            try:
                line_ver, line_path = line.strip().split(maxsplit=1)
            except ValueError:
                # got less values to unpack
                continue

            # strip invalid characters in line_path
            invalid_chars = "/\0"  # \0 is NUL
            if platform.system() == "Windows":
                invalid_chars += '<>:"\\|?*'

            line_path = line_path.strip(invalid_chars)
            try:
                if (
                    line_ver == pylauncher_version
                    and Path(line_path).resolve() == sys_executable_path.resolve()
                ):
                    return f"py {line_ver}"
            except RuntimeError:
                # happens when resolve() encounters an infinite loop
                pass

    # Returning sys.executable is reliable, but this does not accommodate for
    # spaces in the path string. Currently it is not possible to workaround
    # without knowing the user's shell.
    # Thus, it won't be done until possible through the standard library.
    # Do not be tempted to use the undocumented subprocess.list2cmdline, it is
    # considered an internal implementation detail for a reason.
    return sys.executable


def pip_self_version_check(session: PipSession, options: optparse.Values) -> None:
    """Check for an update for pip.

    Limit the frequency of checks to once per week. State is stored either in
    the active virtualenv or in the user's USER_CACHE_DIR keyed off the prefix
    of the pip script path.
    """
    installed_dist = get_default_environment().get_distribution("pip")
    if not installed_dist:
        return

    pip_version = installed_dist.version
    pypi_version = None

    try:
        state = SelfCheckState(cache_dir=options.cache_dir)

        current_time = datetime.datetime.utcnow()
        # Determine if we need to refresh the state
        if "last_check" in state.state and "pypi_version" in state.state:
            last_check = datetime.datetime.strptime(
                state.state["last_check"], SELFCHECK_DATE_FMT
            )
            if (current_time - last_check).total_seconds() < 7 * 24 * 60 * 60:
                pypi_version = state.state["pypi_version"]

        # Refresh the version if we need to or just see if we need to warn
        if pypi_version is None:
            # Lets use PackageFinder to see what the latest pip version is
            link_collector = LinkCollector.create(
                session,
                options=options,
                suppress_no_index=True,
            )

            # Pass allow_yanked=False so we don't suggest upgrading to a
            # yanked version.
            selection_prefs = SelectionPreferences(
                allow_yanked=False,
                allow_all_prereleases=False,  # Explicitly set to False
            )

            finder = PackageFinder.create(
                link_collector=link_collector,
                selection_prefs=selection_prefs,
                use_deprecated_html5lib=(
                    "html5lib" in options.deprecated_features_enabled
                ),
            )
            best_candidate = finder.find_best_candidate("pip").best_candidate
            if best_candidate is None:
                return
            pypi_version = str(best_candidate.version)

            # save that we've performed a check
            state.save(pypi_version, current_time)

        remote_version = parse_version(pypi_version)

        local_version_is_older = (
            pip_version < remote_version
            and pip_version.base_version != remote_version.base_version
            and was_installed_by_pip("pip")
        )

        # Determine if our pypi_version is older
        if not local_version_is_older:
            return

        pip_cmd = f"{get_py_executable()} -m pip"
        logger.warning(
            "You are using pip version %s; however, version %s is "
            "available.\nYou should consider upgrading via the "
            "'%s install --upgrade pip' command.",
            pip_version,
            pypi_version,
            pip_cmd,
        )
    except Exception:
        logger.debug(
            "There was an error checking the latest version of pip",
            exc_info=True,
        )
