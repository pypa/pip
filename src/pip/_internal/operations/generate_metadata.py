"""Metadata generation logic for source distributions.
"""

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable
    from pip._internal.req.req_install import InstallRequirement


def get_metadata_generator(install_req):
    # type: (InstallRequirement) -> Callable[[InstallRequirement], None]
    if not install_req.use_pep517:
        return _generate_metadata_legacy

    return _generate_metadata


def _generate_metadata_legacy(install_req):
    # type: (InstallRequirement) -> None
    install_req.run_egg_info()


def _generate_metadata(install_req):
    # type: (InstallRequirement) -> None
    install_req.prepare_pep517_metadata()
