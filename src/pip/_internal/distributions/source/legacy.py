import logging

from pip._internal.distributions.base import AbstractDistribution

logger = logging.getLogger(__name__)


class LegacySourceDistribution(AbstractDistribution):
    """Represents a legacy source distribution.

    These distributions are based on a de-facto standard between pip and
    setuptools, built upon the command line interface of 'setup.py'.
    """

    def get_pkg_resources_distribution(self):
        return self.req.get_dist()

    def prepare_distribution_metadata(self, finder, build_isolation):
        self.req.prepare_metadata()
        self.req.assert_source_matches_version()
