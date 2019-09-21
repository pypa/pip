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
    if install_req.name:
        logger.debug(
            'Running setup.py (path:%s) egg_info for package %s',
            install_req.setup_py_path, install_req.name,
        )
    else:
        logger.debug(
            'Running setup.py (path:%s) egg_info for package from %s',
            install_req.setup_py_path, install_req.link,
        )

    base_cmd = make_setuptools_shim_args(install_req.setup_py_path)
    if install_req.isolated:
        base_cmd += ["--no-user-cfg"]
    egg_info_cmd = base_cmd + ['egg_info']
    # We can't put the .egg-info files at the root, because then the
    # source code will be mistaken for an installed egg, causing
    # problems
    if install_req.editable:
        egg_base_option = []  # type: List[str]
    else:
        egg_info_dir = os.path.join(install_req.setup_py_dir, 'pip-egg-info')
        ensure_dir(egg_info_dir)
        egg_base_option = ['--egg-base', 'pip-egg-info']
    with install_req.build_env:
        call_subprocess(
            egg_info_cmd + egg_base_option,
            cwd=install_req.setup_py_dir,
            command_desc='python setup.py egg_info')


def _generate_metadata(install_req):
    # type: (InstallRequirement) -> None
    install_req.prepare_pep517_metadata()
