from pip._vendor import pkg_resources

from pip._internal.distributions.base import AbstractDistribution


class WheelDistribution(AbstractDistribution):

    def dist(self):
        return list(pkg_resources.find_distributions(
                    self.req.source_dir))[0]

    def prep_for_dist(self, finder, build_isolation):
        pass
