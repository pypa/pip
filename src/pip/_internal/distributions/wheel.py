from pip._vendor import pkg_resources

from pip._internal.distributions.base import AbstractDistribution
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from pip._vendor.pkg_resources import Distribution
    from pip._internal.index.package_finder import PackageFinder


class WheelDistribution(AbstractDistribution):
    """Represents a wheel distribution.

    This does not need any preparation as wheels can be directly unpacked.
    """

    def get_pkg_resources_distribution(self):
        # type: () -> Distribution
        return list(pkg_resources.find_distributions(
                    self.req.source_dir))[0]

    def prepare_distribution_metadata(self, finder, build_isolation):
        # type: (PackageFinder, bool) -> None
        pass
