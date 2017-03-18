"""Configuration management setup
"""

import re
import os
import sys

from pip._vendor.six.moves import configparser
from pip.locations import (
    legacy_config_file, config_basename, running_under_virtualenv,
    site_config_files
)
from pip.utils import appdirs


_environ_prefix_re = re.compile(r"^PIP_", re.I)


class Configuration(object):
    """Handles the loading of configuration files and providing an interface to
    accessing data within them.
    """

    def __init__(self, isolated):
        self._configparser = configparser.RawConfigParser()
        self._config = {}
        self.isolated = isolated

    def load(self, section):
        """Loads configuration
        """
        self._load_config_files(section)
        if not self.isolated:
            self._load_environment_vars()

    def items(self):
        """Returns key-value pairs like dict.values() representing the loaded
        configuration
        """
        return self._config.items()

    def _load_config_files(self, section):
        """Loads configuration from configuration files
        """
        files = self._get_config_files()

        if files:
            self._configparser.read(files)

        for section in ('global', section):
            self._config.update(
                self._normalize_keys(self._get_config_section(section))
            )

    def _load_environment_vars(self):
        """Loads configuration from environment variables
        """
        self._config.update(self._normalize_keys(self._get_environ_vars()))

    def _normalize_keys(self, items):
        """Return a config dictionary with normalized keys regardless of
        whether the keys were specified in environment variables or in config
        files"""
        normalized = {}
        for key, val in items:
            key = key.replace('_', '-')
            if key.startswith('--'):
                key = key[2:]  # only prefer long opts
            normalized[key] = val
        return normalized

    def _get_environ_vars(self):
        """Returns a generator with all environmental vars with prefix PIP_"""
        for key, val in os.environ.items():
            if _environ_prefix_re.search(key):
                yield (_environ_prefix_re.sub("", key).lower(), val)

    def _get_config_files(self):
        """Returns configuration files in a defined order.

        The order is that the first files are overridden by the latter files;
        like what ConfigParser expects.
        """
        # the files returned by this method will be parsed in order with the
        # first files listed being overridden by later files in standard
        # ConfigParser fashion
        config_file = os.environ.get('PIP_CONFIG_FILE', False)
        if config_file == os.devnull:
            return []

        # at the base we have any site-wide configuration
        files = list(site_config_files)

        # per-user configuration next
        if not self.isolated:
            if config_file and os.path.exists(config_file):
                files.append(config_file)
            else:
                # This is the legacy config file, we consider it to be a lower
                # priority than the new file location.
                files.append(legacy_config_file)

                # This is the new config file, we consider it to be a higher
                # priority than the legacy file.
                files.append(
                    os.path.join(
                        appdirs.user_config_dir("pip"),
                        config_basename,
                    )
                )

        # finally virtualenv configuration first trumping others
        if running_under_virtualenv():
            venv_config_file = os.path.join(
                sys.prefix,
                config_basename,
            )
            if os.path.exists(venv_config_file):
                files.append(venv_config_file)

        return files

    def _get_config_section(self, section):
        if self._configparser.has_section(section):
            return self._configparser.items(section)
        return []
