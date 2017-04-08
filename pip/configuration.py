"""Configuration management setup

Some terminology:
- name
  As written in config files.
- value
  Value associated with a name
- key
  Name combined with it's section (section.name)
- variant
  A single word describing where the configuration key-value pair came from
"""

import os
import re
import logging

from pip._vendor.six import next
from pip._vendor.six.moves import configparser

from pip.exceptions import ConfigurationError
from pip.locations import (
    legacy_config_file, new_config_file, running_under_virtualenv,
    site_config_files, venv_config_file
)
from pip.utils import ensure_dir

_environ_prefix_re = re.compile(r"^PIP_", re.I)
_need_file_err_msg = "Needed a specific file to be modifying."


logger = logging.getLogger(__name__)


# NOTE: Maybe use the optionx attribute to normalize keynames.
def _normalize_name(name):
    """Make a name consistent regardless of source (environment or file)
    """
    name = name.lower().replace('_', '-')
    if name.startswith('--'):
        name = name[2:]  # only prefer long opts
    return name


def _disassemble_key(name):
    return name.split(".", 1)


def _make_key(variant, name):
    return ".".join((variant, name))


class Configuration(object):
    """Handles management of configuration.

    Provides an interface to accessing and managing configuration files.

    This class converts provides an API that takes "section.key-name" style
    keys and stores the value associated with it as "key-name" under the
    section "section".

    This allows for a clean interface wherein the both the section and the
    key-name are preserved in an easy to manage form in the configuration files
    and the data stored is also nice.
    """

    def __init__(self, isolated, load_only=None):
        super(Configuration, self).__init__()

        if load_only not in ["user", "site-wide", "venv", None]:
            raise ConfigurationError(
                "Got invalid value for load_only - should be one of 'user', "
                "'site-wide', 'venv'"
            )
        self.isolated = isolated
        self.load_only = load_only

        # The order here determines the override order.
        self._override_order = ["site-wide", "user", "venv", "environment"]
        # Because we keep track of where we got the data from
        self._parsers = {variant: [] for variant in self._override_order}
        self._config = {variant: {} for variant in self._override_order}
        self._modified_parsers = []

    def load(self):
        """Loads configuration from configuration files and environment
        """
        self._load_config_files()
        if not self.isolated:
            self._load_environment_vars()

    def items(self):
        """Returns key-value pairs like dict.items() representing the loaded
        configuration
        """
        return self._dictionary.items()

    def get_value(self, key):
        """Get a value from the configuration.
        """
        return self._dictionary[key]

    def set_value(self, key, value):
        """Modify a value in the configuration.
        """
        assert self.load_only is not None, _need_file_err_msg

        file, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)

            # Modify the parser and the configuration
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, name, value)

        self._config[self.load_only][key] = value

        # MARK:: Maybe DRY this.
        file_parser_tuple = (file, parser)
        if file_parser_tuple not in self._modified_parsers:
            self._modified_parsers.append(file_parser_tuple)

    def unset_value(self, key):
        """Unset a value in the configuration.
        """
        assert self.load_only is not None, _need_file_err_msg

        if key not in self._config[self.load_only]:
            raise ConfigurationError(key)

        file, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)

            # Remove the key in the parser
            modified_something = (
                parser.has_section(section) and
                parser.remove_option(section, name)
            )

            if modified_something:
                # name removed from parser, section may now be empty
                if next(iter(parser.items(section)), None) is None:
                    parser.remove_section(section)

                # MARK:: Maybe DRY this.
                file_parser_tuple = (file, parser)
                if file_parser_tuple not in self._modified_parsers:
                    self._modified_parsers.append(file_parser_tuple)
            else:
                raise ConfigurationError(
                    "Internal error [id=1]. Please report as a bug."
                )

        del self._config[self.load_only][key]

        return True

    def save(self):
        assert self.load_only is not None, _need_file_err_msg

        for file, parser in self._modified_parsers:
            logger.info("Writing to %s", file)

            # Ensure directory exists.
            ensure_dir(os.path.dirname(file))

            with open(file, "w") as f:
                parser.write(f)

    #
    # Private routines
    #

    @property
    def _dictionary(self):
        """A dictionary representing the loaded configuration.
        """
        # NOTE: Dictionaries are not populated if not loaded. So, conditionals
        #       are not needed here.
        retval = {}

        for variant in self._override_order:
            retval.update(self._config[variant])

        return retval

    def _load_config_files(self):
        """Loads configuration from configuration files
        """
        for variant, files in self._get_config_files():
            for file in files:
                # If there's specific variant set in `load_only`, load only
                # that variant, not the others.
                if self.load_only is not None and variant != self.load_only:
                    continue

                parser = self._load_file(variant, file)

                # Keeping track of the parsers used
                self._parsers[variant].append((file, parser))

    def _load_file(self, variant, file):
        parser = self._construct_parser(file)

        for section in parser.sections():
            self._config[variant].update(
                self._normalized_keys(section, parser.items(section))
            )
        return parser

    def _construct_parser(self, file):
        parser = configparser.RawConfigParser()
        # If there is no such file, don't bother reading it but create the
        # parser anyway, to hold the data.
        # Doing this is useful when modifying and saving files, where we don't
        # need to construct a parser.
        if os.path.exists(file):
            parser.read(file)

        return parser

    def _load_environment_vars(self):
        """Loads configuration from environment variables
        """
        self._config["environment"].update(
            self._normalized_keys(":env:", self._get_environ_vars())
        )

    def _normalized_keys(self, section, items):
        """Normalizes items to construct a dictionary with normalized keys.

        This routine is where the names become keys and are made the same
        regardless of source - configuration files or environment.
        """
        normalized = {}
        for name, val in items:
            key = _make_key(section, _normalize_name(name))

            normalized[key] = val
        return normalized

    def _get_environ_vars(self):
        """Returns a generator with all environmental vars with prefix PIP_"""
        for key, val in os.environ.items():
            if _environ_prefix_re.search(key):
                yield (_environ_prefix_re.sub("", key).lower(), val)

    def _get_config_files(self):
        """Yields variant and configuration files associated with it.

        This should be treated like items of a dictionary.
        """

        config_file = os.environ.get('PIP_CONFIG_FILE', False)
        if config_file == os.devnull:
            return

        # at the base we have any site-wide configuration
        yield "site-wide", list(site_config_files)

        # per-user configuration next
        if not self.isolated:
            if config_file and os.path.exists(config_file):
                yield "user", [config_file]
            else:
                # The legacy config file is overridden by the new config file
                yield "user", [legacy_config_file, new_config_file]

        # finally virtualenv configuration first trumping others
        if running_under_virtualenv():
            yield "venv", [venv_config_file]

    def _get_parser_to_modify(self):
        # Determine which parser to modify
        parsers = self._parsers[self.load_only]
        if not parsers:
            # This should not happen if everything works correctly.
            raise ConfigurationError(
                "Internal error [id=2]. Please report as a bug."
            )

        # Use the highest priority parser.
        return parsers[-1]
