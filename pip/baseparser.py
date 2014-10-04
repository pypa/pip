"""Base option parser setup"""
from __future__ import absolute_import
from __future__ import print_function

if True:
    # distutils and six.moves can't be statically analysed
    # pylint:disable=import-error
    from distutils.util import strtobool
    from pip._vendor.six.moves import configparser

import sys
import optparse
import os
import textwrap

from pip._vendor.six import string_types
from pip.locations import (
    legacy_config_file, config_basename, running_under_virtualenv,
    site_config_files
)
from pip.utils import appdirs, get_terminal_size


class PrettyHelpFormatter(optparse.IndentedHelpFormatter):
    """A prettier/less verbose help formatter for optparse."""

    def __init__(self, *args, **kwargs):
        # help position must be aligned with __init__.parseopts.description
        kwargs['max_help_position'] = 30
        kwargs['indent_increment'] = 1
        kwargs['width'] = get_terminal_size()[0] - 2
        optparse.IndentedHelpFormatter.__init__(self, *args, **kwargs)

    def format_option_strings(self, option):
        return _format_option_strings(option, ' <%s>', ', ')

    def format_heading(self, heading):
        if heading == 'Options':
            return ''
        return heading + ':\n'

    def format_usage(self, usage):
        """
        Ensure there is only one newline between usage and the first heading
        if there is no description.
        """
        msg = '\nUsage: %s\n' % indent_lines(textwrap.dedent(usage), "  ")
        return msg

    def format_description(self, description):
        # leave full control over description to us
        if description:
            if hasattr(self.parser, 'main'):
                label = 'Commands'
            else:
                label = 'Description'
            # some doc strings have initial newlines, some don't
            description = description.lstrip('\n')
            # some doc strings have final newlines and spaces, some don't
            description = description.rstrip()
            # dedent, then reindent
            description = indent_lines(textwrap.dedent(description), "  ")
            description = '%s:\n%s\n' % (label, description)
            return description
        else:
            return ''

    def format_epilog(self, epilog):
        # leave full control over epilog to us
        if epilog:
            return epilog
        else:
            return ''


class UpdatingDefaultsHelpFormatter(PrettyHelpFormatter):
    """Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing"""

    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class CustomOptionParser(optparse.OptionParser):
    # pylint:disable=too-many-public-methods
    def insert_option_group(self, idx, *args, **kwargs):
        """Insert an OptionGroup at a given position."""
        group = self.add_option_group(*args, **kwargs)

        self.option_groups.pop()
        self.option_groups.insert(idx, group)

        return group

    @property
    def option_list_all(self):
        """Get a list of all options, including those in option groups."""
        res = self.option_list[:]
        for i in self.option_groups:
            res.extend(i.option_list)

        return res


class ConfigOptionParser(CustomOptionParser):
    """Custom option parser which updates its defaults by checking the
    configuration files and environmental variables"""
    # pylint:disable=too-many-public-methods

    def __init__(self, *args, **kwargs):
        self.config = configparser.RawConfigParser()
        self.name = kwargs.pop('name')
        self.files = get_config_files()
        if self.files:
            self.config.read(self.files)
        assert self.name
        CustomOptionParser.__init__(self, *args, **kwargs)

    def update_defaults(self, defaults):
        """Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists)."""
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        for section in ('global', self.name):
            config.update(
                normalize_keys(self.get_config_section(section))
            )
        # 2. environmental variables
        config.update(normalize_keys(get_environ_vars()))
        # Then set the options with those values
        for key, val in config.items():
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                if option.action in ('store_true', 'store_false', 'count'):
                    val = strtobool(val)
                if option.action == 'append':
                    val = val.split()
                    val = [check_default(option, key, v) for v in val]
                else:
                    val = check_default(option, key, val)

                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """Get a section of a configuration"""
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_default_values(self):
        """Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work."""
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, string_types):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)

    def error(self, msg):
        self.print_usage(sys.stderr)
        self.exit(2, "%s\n" % msg)


def get_environ_vars(prefix='PIP_'):
    """Returns a generator with all environmental vars with prefix PIP_"""
    for key, val in os.environ.items():
        if key.startswith(prefix):
            yield (key.replace(prefix, '').lower(), val)


def normalize_keys(items):
    """Return a config dictionary with normalized keys regardless of
    whether the keys were specified in environment variables or in config
    files"""
    normalized = {}
    for key, val in items:
        key = key.replace('_', '-')
        if not key.startswith('--'):
            key = '--%s' % key  # only prefer long opts
        normalized[key] = val
    return normalized


def check_default(option, key, val):
    try:
        return option.check_value(key, val)
    except optparse.OptionValueError as exc:
        print("An error occurred during configuration: %s" % exc)
        sys.exit(3)


def get_config_files():
    # the files returned by this method will be parsed in order with the
    # first files listed being overridden by later files in standard
    # ConfigParser fashion
    config_file = os.environ.get('PIP_CONFIG_FILE', False)
    if config_file == os.devnull:
        return []

    # at the base we have any site-wide configuration
    files = list(site_config_files)

    # per-user configuration next
    if config_file and os.path.exists(config_file):
        files.append(config_file)
    else:
        # This is the legacy config file, we consider it to be a lower
        # priority than the new file location.
        files.append(legacy_config_file)

        # This is the new config file, we consider it to be a higher
        # priority than the legacy file.
        files.append(
            os.path.join(appdirs.user_config_dir("pip"), config_basename)
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


def indent_lines(text, indent):
    new_lines = [indent + line for line in text.split('\n')]
    return "\n".join(new_lines)


def _format_option_strings(option, mvarfmt=' <%s>', optsep=', '):
    """
    Return a comma-separated list of option strings and metavars.

    :param option:  tuple of (short opt, long opt), e.g: ('-f', '--format')
    :param mvarfmt: metavar format string - evaluated as mvarfmt % metavar
    :param optsep:  separator
    """
    # pylint:disable=protected-access
    opts = []

    if option._short_opts:
        opts.append(option._short_opts[0])
    if option._long_opts:
        opts.append(option._long_opts[0])
    if len(opts) > 1:
        opts.insert(1, optsep)

    if option.takes_value():
        metavar = option.metavar or option.dest.lower()
        opts.append(mvarfmt % metavar.lower())

    return ''.join(opts)
