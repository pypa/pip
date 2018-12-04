from pip._internal.distributions.abc import AbstractDistribution


class InstalledDistribution(AbstractDistribution):

    def get_dist(self):
        return self.req.satisfied_by

    def prepare(self, finder, build_isolation):
        pass
