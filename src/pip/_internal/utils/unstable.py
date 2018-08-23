
from pip._internal.exceptions import UnknownUnstableFeatures


class UnstableFeaturesHelper(object):
    """Handles logic for registering/validating/checking
    """

    def __init__(self):
        super(UnstableFeaturesHelper, self).__init__()
        self._names = set()
        self._enabled_names = set()

    def register(self, *names):
        self._names.update(set(names))

    def validate(self, given_names):
        # Remember the given names as they are "enabled" features
        self._enabled_names = set(given_names)

        unknown_names = self._enabled_names - self._names
        if unknown_names:
            raise UnknownUnstableFeatures(unknown_names)

    def is_enabled(self, name):
        return name in self._enabled_names
