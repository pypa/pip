import abc

from pip._vendor.six import add_metaclass


@add_metaclass(abc.ABCMeta)
class AbstractDistribution(object):

    def __init__(self, req):
        super(AbstractDistribution, self).__init__()
        self.req = req

    @abc.abstractmethod
    def dist(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def prep_for_dist(self, finder, build_isolation):
        raise NotImplementedError()
