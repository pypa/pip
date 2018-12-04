from pip._internal.distributions.source import SourceDistribution as _SrcDist
from pip._internal.distributions.wheel import WheelDistribution as _WhlDist

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from pip._internal.req.req_install import InstallRequirement  # noqa: F401
    from pip._internal.distributions._base import (  # noqa: F401
        AbstractDistribution
    )


def make_abstract_dist(install_req):
    # type: (InstallRequirement) -> AbstractDistribution
    """Returns a Distribution for the given InstallRequirement
    """
    # If it's not an editable, is a wheel, it's a WheelDistribution
    if install_req.editable:
        return _SrcDist(install_req)

    if install_req.link and install_req.is_wheel:
        return _WhlDist(install_req)

    # Otherwise, a SourceDistribution
    return _SrcDist(install_req)
