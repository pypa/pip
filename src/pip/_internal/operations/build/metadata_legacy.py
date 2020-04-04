"""Metadata generation logic for legacy source distributions.
"""

import logging
import os

from pip._internal.exceptions import InstallationError
from pip._internal.utils.setuptools_build import make_setuptools_egg_info_args
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.vcs import vcs

if MYPY_CHECK_RUNNING:
    from typing import List, Optional

    from pip._internal.build_env import BuildEnvironment

logger = logging.getLogger(__name__)


def _find_egg_info(source_directory):
    # type: (str) -> str
    """Find an .egg-info in `source_directory`.
    """

    def looks_like_virtual_env(path):
        # type: (str) -> bool
        return (
            os.path.lexists(os.path.join(path, 'bin', 'python')) or
            os.path.exists(os.path.join(path, 'Scripts', 'Python.exe'))
        )

    def locate_egg_info(base):
        # type: (str) -> List[str]
        candidates = []  # type: List[str]
        for root, dirs, files in os.walk(base):
            for dir_ in vcs.dirnames:
                if dir_ in dirs:
                    dirs.remove(dir_)
            # Iterate over a copy of ``dirs``, since mutating
            # a list while iterating over it can cause trouble.
            # (See https://github.com/pypa/pip/pull/462.)
            for dir_ in list(dirs):
                if looks_like_virtual_env(os.path.join(root, dir_)):
                    dirs.remove(dir_)
                # Also don't search through tests
                elif dir_ == 'test' or dir_ == 'tests':
                    dirs.remove(dir_)
            candidates.extend(os.path.join(root, dir_) for dir_ in dirs)
        return [f for f in candidates if f.endswith('.egg-info')]

    def depth_of_directory(dir_):
        # type: (str) -> int
        return (
            dir_.count(os.path.sep) +
            (os.path.altsep and dir_.count(os.path.altsep) or 0)
        )

    base = source_directory
    filenames = locate_egg_info(base)

    if not filenames:
        raise InstallationError(
            "Files/directories not found in {}".format(base)
        )

    # If we have more than one match, we pick the toplevel one.  This
    # can easily be the case if there is a dist folder which contains
    # an extracted tarball for testing purposes.
    if len(filenames) > 1:
        filenames.sort(key=depth_of_directory)

    return os.path.join(base, filenames[0])


def generate_metadata(
    build_env,  # type: BuildEnvironment
    setup_py_path,  # type: str
    source_dir,  # type: str
    editable,  # type: bool
    isolated,  # type: bool
    details,  # type: str
):
    # type: (...) -> str
    """Generate metadata using setup.py-based defacto mechanisms.

    Returns the generated metadata directory.
    """
    logger.debug(
        'Running setup.py (path:%s) egg_info for package %s',
        setup_py_path, details,
    )

    egg_info_dir = None  # type: Optional[str]
    # For non-editable installs, don't put the .egg-info files at the root,
    # to avoid confusion due to the source code being considered an installed
    # egg.
    if not editable:
        egg_info_dir = TempDirectory(
            kind="pip-egg-info", globally_managed=True
        ).path

    args = make_setuptools_egg_info_args(
        setup_py_path,
        egg_info_dir=egg_info_dir,
        no_user_config=isolated,
    )

    with build_env:
        call_subprocess(
            args,
            cwd=source_dir,
            command_desc='python setup.py egg_info',
        )

    # Return the .egg-info directory.
    if not editable:
        assert egg_info_dir
        return _find_egg_info(egg_info_dir)
    return _find_egg_info(source_dir)
