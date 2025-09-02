from pip._internal.distributions.base import AbstractDistribution
from pip._internal.distributions.installed import InstalledDistribution
from pip._internal.distributions.sdist import SourceDistribution
from pip._internal.distributions.wheel import WheelDistribution
from pip._internal.req.req_install import InstallRequirement


def make_distribution_for_install_requirement(
    install_req: InstallRequirement,
) -> AbstractDistribution:
    """Returns an AbstractDistribution for the given InstallRequirement.

    As AbstractDistribution only covers installable artifacts, this method may only be
    invoked at the conclusion of a resolve, when the RequirementPreparer has downloaded
    the file corresponding to the resolved dist. Commands which intend to consume
    metadata-only resolves without downloading should not call this method or
    consume AbstractDistribution objects.
    """
    # Only pre-installed requirements will have a .satisfied_by dist.
    if install_req.satisfied_by:
        return InstalledDistribution(install_req)

    # Editable requirements will always be source distributions. They use the
    # legacy logic until we create a modern standard for them.
    if install_req.editable:
        return SourceDistribution(install_req)

    # If it's a wheel, it's a WheelDistribution
    if install_req.is_wheel:
        return WheelDistribution(install_req)

    # Otherwise, a SourceDistribution
    return SourceDistribution(install_req)
