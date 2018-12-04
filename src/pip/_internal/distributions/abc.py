class AbstractDistribution(object):
    """A base class that abstracts information about


    The requirements for anything installable are as follows:

     - we must be able to determine the requirement name
       (or we can't correctly handle the non-upgrade case).

     - for packages with setup requirements, we must also be able
       to determine their requirements without installing additional
       packages (for the same reason as run-time dependencies)

     - we must be able to create a Distribution object exposing the
       above metadata.
    """

    def __init__(self, req):
        super(AbstractDistribution, self).__init__()
        self.req = req

    def get_dist(self):
        raise NotImplementedError()

    def prepare(self, finder, build_isolation):
        raise NotImplementedError()
