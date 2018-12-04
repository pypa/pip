from pip._vendor import pkg_resources

from pip._internal.distributions.abc import AbstractDistribution


class WheelDistribution(AbstractDistribution):

    def get_dist(self):
        return list(pkg_resources.find_distributions(
                    self.req.source_dir))[0]

    def prepare(self, finder, build_isolation):
        pass
