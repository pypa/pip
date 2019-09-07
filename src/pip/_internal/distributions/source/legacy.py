import logging

from pip._internal.distributions.base import AbstractDistribution

logger = logging.getLogger(__name__)


class LegacySourceDistribution(AbstractDistribution):
    """Represents a source distribution.

    The preparation step for these needs metadata for the packages to be
    generated, either using PEP 517 or using the legacy `setup.py egg_info`.

    NOTE from @pradyunsg (14 June 2019)
    I expect SourceDistribution class will need to be split into
    `legacy_source` (setup.py based) and `source` (PEP 517 based) when we start
    bringing logic for preparation out of InstallRequirement into this class.
    """

    def get_pkg_resources_distribution(self):
        return self.req.get_dist()

    def prepare_distribution_metadata(self, finder, build_isolation):
        self.req.prepare_metadata()
        self.req.assert_source_matches_version()
