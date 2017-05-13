"""Helpers for tests that check configuration
"""

import functools
import pip.configuration


class ConfigurationPatchingMixin(object):

    def patch_configuration(self, variant, di):
        old = self.configuration._load_file

        @functools.wraps(old)
        def overidden(v, file):
            if variant == v:
                self.configuration._config[v].update(di)
                return object()
            else:
                return old(v, file)
        self.configuration._load_file = overidden

    def setup(self):
        self.configuration = pip.configuration.Configuration(isolated=False)
