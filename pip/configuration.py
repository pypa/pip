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

import logging
import os

from pip._vendor.six import next
from pip._vendor.six.moves import configparser

from pip.exceptions import ConfigurationError
from pip.locations import (
    legacy_config_file, new_config_file, running_under_virtualenv,
    site_config_files, venv_config_file
)
from pip.utils import ensure_dir

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

    def get_file(self):
        """Returns the file with highest priority in configuration
        """
        try:
            return self._get_parser_to_modify()[0]
        except IndexError:
            return None

    def items(self):
        """Returns key-value pairs like dict.items() representing the loaded
        configuration
        """
        return self._dictionary.items()

    def get_value(self, key):
        """Get a value from the configuration.
        """
        try:
            return self._dictionary[key]
        except KeyError:
            raise ConfigurationError("No such key - {}".format(key))

    def set_value(self, key, value):
        """Modify a value in the configuration.
        """
        self._ensure_have_load_only()

        file_, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)

            # Modify the parser and the configuration
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, name, value)

        self._config[self.load_only][key] = value
        self._mark_as_modified(file_, parser)

    def unset_value(self, key):
        """Unset a value in the configuration.
        """
        self._ensure_have_load_only()

        if key not in self._config[self.load_only]:
            raise ConfigurationError("No such key - {}".format(key))

        file_, parser = self._get_parser_to_modify()

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

                self._mark_as_modified(file_, parser)
            else:
                raise ConfigurationError(
                    "Fatal Internal error [id=1]. Please report as a bug."
                )

        del self._config[self.load_only][key]

    def save(self):
        self._ensure_have_load_only()

        for file_, parser in self._modified_parsers:
            logger.info("Writing to %s", file_)

            # Ensure directory exists.
            ensure_dir(os.path.dirname(file_))

            with open(file_, "w") as f:
                parser.write(f)

    #
    # Private routines
    #

    def _ensure_have_load_only(self):
        if self.load_only is None:
            raise ConfigurationError("Needed a specific file to be modifying.")

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
        config_files = dict(self._get_config_files())
        if config_files["environment"][0:1] == [os.devnull]:
            logger.debug(
                "Skipping loading configuration files due to "
                "environment's PIP_CONFIG_FILE being os.devnull"
            )
            return

        for variant, files in config_files.items():
            for file_ in files:
                # If there's specific variant set in `load_only`, load only
                # that variant, not the others.
                if self.load_only is not None and variant != self.load_only:
                    continue

                parser = self._load_file(variant, file_)

                # Keeping track of the parsers used
                self._parsers[variant].append((file_, parser))

    # XXX: This is patched in the tests.
    def _load_file(self, variant, file_):
        logger.debug("For variant '%s', will try loading '%s'", variant, file_)
        parser = self._construct_parser(file_)

        for section in parser.sections():
            items = parser.items(section)
            self._config[variant].update(self._normalized_keys(section, items))

        return parser

    def _construct_parser(self, file_):
        parser = configparser.RawConfigParser()
        # If there is no such file, don't bother reading it but create the
        # parser anyway, to hold the data.
        # Doing this is useful when modifying and saving files, where we don't
        # need to construct a parser.
        if os.path.exists(file_):
            parser.read(file_)

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
            if key.startswith("PIP_"):
                yield key[4:].lower(), val

    def _get_config_files(self):
        """Yields variant and configuration files associated with it.

        This should be treated like items of a dictionary.
        """
        # SMELL: Move the conditions out of this function

        # environment variables have the lowest priority
        config_file = os.environ.get('PIP_CONFIG_FILE', None)
        if config_file is not None:
            yield "environment", [config_file]
        else:
            yield "environment", []

        # at the base we have any site-wide configuration
        yield "site-wide", list(site_config_files)

        # per-user configuration next
        should_load_user_config = not self.isolated and not (
            config_file and os.path.exists(config_file)
        )
        if should_load_user_config:
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
                "Fatal Internal error [id=2]. Please report as a bug."
            )

        # Use the highest priority parser.
        return parsers[-1]

    # XXX: This is patched in the tests.
    def _mark_as_modified(self, file_, parser):
        file_parser_tuple = (file_, parser)
        if file_parser_tuple not in self._modified_parsers:
            self._modified_parsers.append(file_parser_tuple)
