"""
shared options and groups

The principle here is to define options once, but *not* instantiate them globally.
One reason being that options with action='append' can carry state between parses.
pip parse's general options twice internally, and shouldn't pass on state.
To be consistent, all options will follow this design.

"""
import copy
from optparse import OptionGroup, SUPPRESS_HELP, Option
from pip.locations import build_prefix, default_log_file


def make_option_group(group, parser):
    """
    Return an OptionGroup object
    group  -- assumed to be dict with 'name' and 'options' keys
    parser -- an optparse Parser
    """
    option_group = OptionGroup(parser, group['name'])
    for option in group['options']:
        option_group.add_option(option.make())
    return option_group

def make_option_maker(*args, **kwargs):
    """Return an object with 'make()' method for creating the option later"""
    class OptionMaker():
        @staticmethod
        def make():
            args_copy = copy.deepcopy(args)
            kwargs_copy = copy.deepcopy(kwargs)
            return Option(*args_copy, **kwargs_copy)
    return OptionMaker

###########
# options #
###########

help_ = make_option_maker(
    '-h', '--help',
    dest='help',
    action='help',
    help='Show help.')

require_virtualenv = make_option_maker(
    # Run only if inside a virtualenv, bail if not.
    '--require-virtualenv', '--require-venv',
    dest='require_venv',
    action='store_true',
    default=False,
    help=SUPPRESS_HELP)

verbose = make_option_maker(
    '-v', '--verbose',
    dest='verbose',
    action='count',
    default=0,
    help='Give more output. Option is additive, and can be used up to 3 times.')

version = make_option_maker(
    '-V', '--version',
    dest='version',
    action='store_true',
    help='Show version and exit.')

quiet = make_option_maker(
    '-q', '--quiet',
    dest='quiet',
    action='count',
    default=0,
    help='Give less output.')

log = make_option_maker(
    '--log',
    dest='log',
    metavar='file',
    help='Log file where a complete (maximum verbosity) record will be kept.')

log_explicit_levels = make_option_maker(
    # Writes the log levels explicitely to the log'
    '--log-explicit-levels',
    dest='log_explicit_levels',
    action='store_true',
    default=False,
    help=SUPPRESS_HELP)

log_file = make_option_maker(
    # The default log file
    '--local-log', '--log-file',
    dest='log_file',
    metavar='file',
    default=default_log_file,
    help=SUPPRESS_HELP)

no_input = make_option_maker(
    # Don't ask for input
    '--no-input',
    dest='no_input',
    action='store_true',
    default=False,
    help=SUPPRESS_HELP)

proxy = make_option_maker(
    '--proxy',
    dest='proxy',
    type='str',
    default='',
    help="Specify a proxy in the form [user:passwd@]proxy.server:port.")

timeout = make_option_maker(
    '--timeout', '--default-timeout',
    metavar='sec',
    dest='timeout',
    type='float',
    default=15,
    help='Set the socket timeout (default %default seconds).')

default_vcs = make_option_maker(
    # The default version control system for editables, e.g. 'svn'
    '--default-vcs',
    dest='default_vcs',
    type='str',
    default='',
    help=SUPPRESS_HELP)

skip_requirements_regex = make_option_maker(
    # A regex to be used to skip requirements
    '--skip-requirements-regex',
    dest='skip_requirements_regex',
    type='str',
    default='',
    help=SUPPRESS_HELP)

exists_action = make_option_maker(
    # Option when path already exist
    '--exists-action',
    dest='exists_action',
    type='choice',
    choices=['s', 'i', 'w', 'b'],
    default=[],
    action='append',
    metavar='action',
    help="Default action when a path already exists: "
    "(s)witch, (i)gnore, (w)ipe, (b)ackup.")

cert = make_option_maker(
    '--cert',
    dest='cert',
    type='str',
    default='',
    metavar='path',
    help = "Path to alternate CA bundle.")

index_url = make_option_maker(
    '-i', '--index-url', '--pypi-url',
    dest='index_url',
    metavar='URL',
    default='https://pypi.python.org/simple/',
    help='Base URL of Python Package Index (default %default).')

extra_index_url = make_option_maker(
    '--extra-index-url',
    dest='extra_index_urls',
    metavar='URL',
    action='append',
    default=[],
    help='Extra URLs of package indexes to use in addition to --index-url.')

no_index = make_option_maker(
    '--no-index',
    dest='no_index',
    action='store_true',
    default=False,
    help='Ignore package index (only looking at --find-links URLs instead).')

find_links =  make_option_maker(
    '-f', '--find-links',
    dest='find_links',
    action='append',
    default=[],
    metavar='url',
    help="If a url or path to an html file, then parse for links to archives. If a local path or file:// url that's a directory, then look for archives in the directory listing.")

# TODO: Remove after 1.6
use_mirrors = make_option_maker(
    '-M', '--use-mirrors',
    dest='use_mirrors',
    action='store_true',
    default=False,
    help=SUPPRESS_HELP)

# TODO: Remove after 1.6
mirrors = make_option_maker(
    '--mirrors',
    dest='mirrors',
    metavar='URL',
    action='append',
    default=[],
    help=SUPPRESS_HELP)

allow_external = make_option_maker(
    "--allow-external",
    dest="allow_external",
    action="append",
    default=[],
    metavar="PACKAGE",
    help="Allow the installation of externally hosted files",
)

allow_all_external = make_option_maker(
    "--allow-all-external",
    dest="allow_all_external",
    action="store_true",
    default=False,
    help="Allow the installation of all externally hosted files",
)

no_allow_external = make_option_maker(
    "--no-allow-external",
    dest="allow_all_external",
    action="store_false",
    default=False,
    help=SUPPRESS_HELP,
)

allow_unsafe = make_option_maker(
    "--allow-insecure",
    dest="allow_insecure",
    action="append",
    default=[],
    metavar="PACKAGE",
    help="Allow the installation of insecure and unverifiable files",
)

no_allow_unsafe = make_option_maker(
    "--no-allow-insecure",
    dest="allow_all_insecure",
    action="store_false",
    default=False,
    help=SUPPRESS_HELP
)

requirements = make_option_maker(
    '-r', '--requirement',
    dest='requirements',
    action='append',
    default=[],
    metavar='file',
    help='Install from the given requirements file. '
    'This option can be used multiple times.')

use_wheel = make_option_maker(
    '--use-wheel',
    dest='use_wheel',
    action='store_true',
    help='Find and prefer wheel archives when searching indexes and find-links locations. Default to accepting source archives.')

download_cache = make_option_maker(
    '--download-cache',
    dest='download_cache',
    metavar='dir',
    default=None,
    help='Cache downloaded packages in <dir>.')

no_deps = make_option_maker(
    '--no-deps', '--no-dependencies',
    dest='ignore_dependencies',
    action='store_true',
    default=False,
    help="Don't install package dependencies.")

build_dir = make_option_maker(
    '-b', '--build', '--build-dir', '--build-directory',
    dest='build_dir',
    metavar='dir',
    default=build_prefix,
    help='Directory to unpack packages into and build in. '
    'The default in a virtualenv is "<venv path>/build". '
    'The default for global installs is "<OS temp dir>/pip_build_<username>".')

install_options = make_option_maker(
    '--install-option',
    dest='install_options',
    action='append',
    metavar='options',
    help="Extra arguments to be supplied to the setup.py install "
    "command (use like --install-option=\"--install-scripts=/usr/local/bin\"). "
    "Use multiple --install-option options to pass multiple options to setup.py install. "
    "If you are using an option with a directory path, be sure to use absolute path.")

global_options = make_option_maker(
    '--global-option',
    dest='global_options',
    action='append',
    metavar='options',
    help="Extra global options to be supplied to the setup.py "
    "call before the install command.")

no_clean = make_option_maker(
    '--no-clean',
    action='store_true',
    default=False,
    help="Don't clean up build directories.")


##########
# groups #
##########

general_group = {
    'name': 'General Options',
    'options': [
        help_,
        require_virtualenv,
        verbose,
        version,
        quiet,
        log,
        log_explicit_levels,
        log_file,
        no_input,
        proxy,
        timeout,
        default_vcs,
        skip_requirements_regex,
        exists_action,
        cert,
        ]
    }

index_group = {
    'name': 'Package Index Options',
    'options': [
        index_url,
        extra_index_url,
        no_index,
        find_links,
        use_mirrors,
        mirrors,
        allow_external,
        allow_all_external,
        no_allow_external,
        allow_unsafe,
        no_allow_unsafe,
        ]
    }
