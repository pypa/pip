"""Metadata generation logic for source distributions.
"""

import logging
import os

from pip._internal.utils.misc import call_subprocess, ensure_dir
from pip._internal.utils.setuptools_build import make_setuptools_shim_args
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, List
    from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


def get_metadata_generator(install_req):
    # type: (InstallRequirement) -> Callable[[InstallRequirement], None]
    if not install_req.use_pep517:
        return _generate_metadata_legacy

    return _generate_metadata


def _generate_metadata_legacy(install_req):
    # type: (InstallRequirement) -> None
    req_details_str = install_req.name or "from {}".format(install_req.link)
    logger.debug(
        'Running setup.py (path:%s) egg_info for package %s',
        install_req.setup_py_path, req_details_str,
    )

    # Compose arguments for subprocess call
    base_cmd = make_setuptools_shim_args(install_req.setup_py_path)
    if install_req.isolated:
        base_cmd += ["--no-user-cfg"]

    # For non-editable installs, don't put the .egg-info files at the root,
    # to avoid confusion due to the source code being considered an installed
    # egg.
    egg_base_option = []  # type: List[str]
    if not install_req.editable:
        egg_info_dir = os.path.join(install_req.setup_py_dir, 'pip-egg-info')
        egg_base_option = ['--egg-base', egg_info_dir]

        # setuptools complains if the target directory does not exist.
        ensure_dir(egg_info_dir)

    with install_req.build_env:
        call_subprocess(
            base_cmd + ["egg_info"] + egg_base_option,
            cwd=install_req.setup_py_dir,
            command_desc='python setup.py egg_info',
        )


def _generate_metadata(install_req):
    # type: (InstallRequirement) -> None
    install_req.prepare_pep517_metadata()
