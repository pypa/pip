"""Helpers for tests that check configuration
"""

import contextlib
import functools
import os
import tempfile
import textwrap
from mock import patch

import pip.configuration
from pip.utils import ensure_dir

# This is so that tests don't need to import pip.configuration
kinds = pip.configuration.kinds


class ConfigurationFileIOMixin(object):

    def setup(self):
        self._patches_to_clear = []

    def teardown(self):
        for patch_obj in self._patches_to_clear:
            patch_obj.stop()

    @contextlib.contextmanager
    def patched_file(self, kind, contents):
        # Create a temporary file
        _, path = tempfile.mkstemp(
            prefix="pip_", suffix="_" + kind + "config.ini", text=True
        )

        contents = textwrap.dedent(contents)
        ensure_dir(os.path.dirname(path))
        with open(path, "w") as f:
            f.write(contents)

        # Convert kind to attribute
        kind_to_attribute_mapping = {
            kinds.VENV: "pip.configuration.venv_config_file",
            kinds.USER: "pip.configuration.new_config_file",
            kinds.GLOBAL: "pip.configuration.site_config_files",
        }

        # Patch the attribute
        # FIXME: This won't work. There's subprocesses!
        patch_to_make = patch(kind_to_attribute_mapping[kind], path)
        patch_to_make.start()
        self._patches_to_clear.append(patch_to_make)

        yield

        os.remove(path)

    @staticmethod
    def get_file_contents(path):
        with open(path) as f:
            return f.read()


class ConfigurationPatchingMixin(object):

    def patch_configuration(self, variant, di):
        old = self.configuration._load_file

        @functools.wraps(old)
        def overidden(v, file_):
            if variant == v:
                self.configuration._config[v].update(di)
                return object()
            else:
                return old(v, file_)
        self.configuration._load_file = overidden

    def setup(self):
        self.configuration = pip.configuration.Configuration(isolated=False)
