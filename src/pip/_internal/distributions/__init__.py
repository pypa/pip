from pip._internal.distributions.source.legacy import LegacySourceDistribution
from pip._internal.distributions.source.modern import ModernSourceDistribution
from pip._internal.distributions.wheel import WheelDistribution

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from pip._internal.distributions.base import AbstractDistribution
    from pip._internal.req.req_install import InstallRequirement


def make_distribution_for_install_requirement(install_req):
    # type: (InstallRequirement) -> AbstractDistribution
    """Returns a Distribution for the given InstallRequirement
    """
    # Editable requirements will always be source distributions. They use the
    # legacy logic until we create a modern standard for them.
    if install_req.editable:
        return LegacySourceDistribution(install_req)

    # If it's a wheel, it's a WheelDistribution
    if install_req.is_wheel:
        return WheelDistribution(install_req)

    # Since legacy and standard-backed (PEP 517) build logic differs, we
    # construct the appropriate kind of Distribution for them, after checking
    # the pyproject.toml file in the distribution.
    install_req.load_pyproject_toml()

    if not install_req.use_pep517:
        return LegacySourceDistribution(install_req)

    return ModernSourceDistribution(install_req)
