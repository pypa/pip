#!/usr/bin/env python
import sys
import os
import errno
import stat
import optparse
import pkg_resources
import urllib2
import urllib
import mimetypes
import zipfile
import tarfile
import tempfile
import subprocess
import posixpath
import re
import shutil
import fnmatch
import operator
import copy
try:
    from hashlib import md5
except ImportError:
    import md5 as md5_module
    md5 = md5_module.new
import urlparse
from email.FeedParser import FeedParser
import traceback
from cStringIO import StringIO
import socket
from Queue import Queue
from Queue import Empty as QueueEmpty
import threading
import httplib
import time
import logging
import ConfigParser
from distutils.util import strtobool
from distutils import sysconfig

class InstallationError(Exception):
    """General exception during installation"""

class UninstallationError(Exception):
    """General exception during uninstallation"""

class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""

class BadCommand(Exception):
    """Raised when virtualenv or a command is not found"""

try:
    any
except NameError:
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

if getattr(sys, 'real_prefix', None):
    ## FIXME: is build/ a good name?
    build_prefix = os.path.join(sys.prefix, 'build')
    src_prefix = os.path.join(sys.prefix, 'src')
else:
    ## FIXME: this isn't a very good default
    build_prefix = os.path.join(os.getcwd(), 'build')
    src_prefix = os.path.join(os.getcwd(), 'src')

# FIXME doesn't account for venv linked to global site-packages

site_packages = sysconfig.get_python_lib()
user_dir = os.path.expanduser('~')
if sys.platform == 'win32':
    bin_py = os.path.join(sys.prefix, 'Scripts')
    # buildout uses 'bin' on Windows too?
    if not os.path.exists(bin_py):
        bin_py = os.path.join(sys.prefix, 'bin')
    config_dir = os.environ.get('APPDATA', user_dir) # Use %APPDATA% for roaming
    default_config_file = os.path.join(config_dir, 'pip', 'pip.ini')
else:
    bin_py = os.path.join(sys.prefix, 'bin')
    default_config_file = os.path.join(user_dir, '.pip', 'pip.conf')
    # Forcing to use /usr/local/bin for standard Mac OS X framework installs
    if sys.platform[:6] == 'darwin' and sys.prefix[:16] == '/System/Library/':
        bin_py = '/usr/local/bin'

class UpdatingDefaultsHelpFormatter(optparse.IndentedHelpFormatter):
    """Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing"""

    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class ConfigOptionParser(optparse.OptionParser):
    """Custom option parser which updates its defaults by by checking the
    configuration files and environmental variables"""

    def __init__(self, *args, **kwargs):
        self.config = ConfigParser.RawConfigParser()
        self.name = kwargs.pop('name')
        self.files = self.get_config_files()
        self.config.read(self.files)
        assert self.name
        optparse.OptionParser.__init__(self, *args, **kwargs)

    def get_config_files(self):
        config_file = os.environ.get('PIP_CONFIG_FILE', False)
        if config_file and os.path.exists(config_file):
            return [config_file]
        return [default_config_file]

    def update_defaults(self, defaults):
        """Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists)."""
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        for section in ('global', self.name):
            config.update(dict(self.get_config_section(section)))
        # 2. environmental variables
        config.update(dict(self.get_environ_vars()))
        # Then set the options with those values
        for key, val in config.iteritems():
            key = key.replace('_', '-')
            if not key.startswith('--'):
                key = '--%s' % key # only prefer long opts
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                # handle multiline configs
                if option.action == 'append':
                    val = val.split()
                else:
                    option.nargs = 1
                if option.action in ('store_true', 'store_false', 'count'):
                    val = strtobool(val)
                try:
                    val = option.convert_value(key, val)
                except optparse.OptionValueError, e:
                    print ("An error occured during configuration: %s" % e)
                    sys.exit(3)
                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """Get a section of a configuration"""
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_environ_vars(self, prefix='PIP_'):
        """Returns a generator with all environmental vars with prefix PIP_"""
        for key, val in os.environ.iteritems():
            if key.startswith(prefix):
                yield (key.replace(prefix, '').lower(), val)

    def get_default_values(self):
        """Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work."""
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy()) # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)

try:
    pip_dist = pkg_resources.get_distribution('pip')
    version = '%s from %s (python %s)' % (
        pip_dist, pip_dist.location, sys.version[:3])
except pkg_resources.DistributionNotFound:
    # when running pip.py without installing
    version=None

def rmtree_errorhandler(func, path, exc_info):
    """On Windows, the files in .svn are read-only, so when rmtree() tries to
    remove them, an exception is thrown.  We catch that here, remove the
    read-only attribute, and hopefully continue without problems."""
    exctype, value = exc_info[:2]
    # lookin for a windows error
    if exctype is not WindowsError or 'Access is denied' not in str(value):
        raise
    # file type should currently be read only
    if ((os.stat(path).st_mode & stat.S_IREAD) != stat.S_IREAD):
        raise
    # convert to read/write
    os.chmod(path, stat.S_IWRITE)
    # use the original function to repeat the operation
    func(path)

class VcsSupport(object):
    _registry = {}
    schemes = ['ssh', 'git', 'hg', 'bzr', 'sftp']

    def __init__(self):
        # Register more schemes with urlparse for various version control systems
        urlparse.uses_netloc.extend(self.schemes)
        urlparse.uses_fragment.extend(self.schemes)
        super(VcsSupport, self).__init__()

    def __iter__(self):
        return self._registry.__iter__()

    @property
    def backends(self):
        return self._registry.values()

    @property
    def dirnames(self):
        return [backend.dirname for backend in self.backends]

    @property
    def all_schemes(self):
        schemes = []
        for backend in self.backends:
            schemes.extend(backend.schemes)
        return schemes

    def register(self, cls):
        if not hasattr(cls, 'name'):
            logger.warn('Cannot register VCS %s' % cls.__name__)
            return
        if cls.name not in self._registry:
            self._registry[cls.name] = cls

    def unregister(self, cls=None, name=None):
        if name in self._registry:
            del self._registry[name]
        elif cls in self._registry.values():
            del self._registry[cls.name]
        else:
            logger.warn('Cannot unregister because no class or name given')

    def get_backend_name(self, location):
        """
        Return the name of the version control backend if found at given
        location, e.g. vcs.get_backend_name('/path/to/vcs/checkout')
        """
        for vc_type in self._registry.values():
            path = os.path.join(location, vc_type.dirname)
            if os.path.exists(path):
                return vc_type.name
        return None

    def get_backend(self, name):
        name = name.lower()
        if name in self._registry:
            return self._registry[name]

    def get_backend_from_location(self, location):
        vc_type = self.get_backend_name(location)
        if vc_type:
            return self.get_backend(vc_type)
        return None

vcs = VcsSupport()

parser = ConfigOptionParser(
    usage='%prog COMMAND [OPTIONS]',
    version=version,
    add_help_option=False,
    formatter=UpdatingDefaultsHelpFormatter(),
    name='global')

parser.add_option(
    '-h', '--help',
    dest='help',
    action='store_true',
    help='Show help')
parser.add_option(
    '-E', '--environment',
    dest='venv',
    metavar='DIR',
    help='virtualenv environment to run pip in (either give the '
    'interpreter or the environment base directory)')
parser.add_option(
    '-s', '--enable-site-packages',
    dest='site_packages',
    action='store_true',
    help='Include site-packages in virtualenv if one is to be '
    'created. Ignored if --environment is not used or '
    'the virtualenv already exists.')
parser.add_option(
    # Defines a default root directory for virtualenvs, relative
    # virtualenvs names/paths are considered relative to it.
    '--virtualenv-base',
    dest='venv_base',
    type='str',
    default='',
    help=optparse.SUPPRESS_HELP)
parser.add_option(
    # Run only if inside a virtualenv, bail if not.
    '--require-virtualenv', '--require-venv',
    dest='require_venv',
    action='store_true',
    default=False,
    help=optparse.SUPPRESS_HELP)
parser.add_option(
    # Use automatically an activated virtualenv instead of installing
    # globally. -E will be ignored if used.
    '--respect-virtualenv', '--respect-venv',
    dest='respect_venv',
    action='store_true',
    default=False,
    help=optparse.SUPPRESS_HELP)

parser.add_option(
    '-v', '--verbose',
    dest='verbose',
    action='count',
    default=0,
    help='Give more output')
parser.add_option(
    '-q', '--quiet',
    dest='quiet',
    action='count',
    default=0,
    help='Give less output')
parser.add_option(
    '--log',
    dest='log',
    metavar='FILENAME',
    help='Log file where a complete (maximum verbosity) record will be kept')
parser.add_option(
    # Writes the log levels explicitely to the log'
    '--log-explicit-levels',
    dest='log_explicit_levels',
    action='store_true',
    default=False,
    help=optparse.SUPPRESS_HELP)
parser.add_option(
    # The default log file
    '--local-log', '--log-file',
    dest='log_file',
    metavar='FILENAME',
    default='./pip-log.txt',
    help=optparse.SUPPRESS_HELP)

parser.add_option(
    '--proxy',
    dest='proxy',
    type='str',
    default='',
    help="Specify a proxy in the form user:passwd@proxy.server:port. "
    "Note that the user:password@ is optional and required only if you "
    "are behind an authenticated proxy.  If you provide "
    "user@proxy.server:port then you will be prompted for a password.")
parser.add_option(
    '--timeout', '--default-timeout',
    metavar='SECONDS',
    dest='timeout',
    type='float',
    default=15,
    help='Set the socket timeout (default %default seconds)')
parser.add_option(
    # The default version control system for editables, e.g. 'svn'
    '--default-vcs',
    dest='default_vcs',
    type='str',
    default='',
    help=optparse.SUPPRESS_HELP)
parser.add_option(
    # A regex to be used to skip requirements
    '--skip-requirements-regex',
    dest='skip_requirements_regex',
    type='str',
    default='',
    help=optparse.SUPPRESS_HELP)

parser.disable_interspersed_args()

_commands = {}

class Command(object):
    name = None
    usage = None
    hidden = False
    def __init__(self):
        assert self.name
        self.parser = ConfigOptionParser(
            usage=self.usage,
            prog='%s %s' % (sys.argv[0], self.name),
            version=parser.version,
            formatter=UpdatingDefaultsHelpFormatter(),
            name=self.name)
        for option in parser.option_list:
            if not option.dest or option.dest == 'help':
                # -h, --version, etc
                continue
            self.parser.add_option(option)
        _commands[self.name] = self

    def merge_options(self, initial_options, options):
        # Make sure we have all global options carried over
        for attr in ['log', 'venv', 'proxy', 'venv_base', 'require_venv',
                     'respect_venv', 'log_explicit_levels', 'log_file',
                     'timeout', 'default_vcs', 'skip_requirements_regex']:
            setattr(options, attr, getattr(initial_options, attr) or getattr(options, attr))
        options.quiet += initial_options.quiet
        options.verbose += initial_options.verbose

    def main(self, complete_args, args, initial_options):
        global logger
        options, args = self.parser.parse_args(args)
        self.merge_options(initial_options, options)

        if options.require_venv and not options.venv:
            # If a venv is required check if it can really be found
            if not os.environ.get('VIRTUAL_ENV'):
                print 'Could not find an activated virtualenv (required).'
                sys.exit(3)
            # Automatically install in currently activated venv if required
            options.respect_venv = True

        if args and args[-1] == '___VENV_RESTART___':
            ## FIXME: We don't do anything this this value yet:
            venv_location = args[-2]
            args = args[:-2]
            options.venv = None
        else:
            # If given the option to respect the activated environment
            # check if no venv is given as a command line parameter
            if options.respect_venv and os.environ.get('VIRTUAL_ENV'):
                if options.venv and os.path.exists(options.venv):
                    # Make sure command line venv and environmental are the same
                    if (os.path.realpath(os.path.expanduser(options.venv)) !=
                            os.path.realpath(os.environ.get('VIRTUAL_ENV'))):
                        print ("Given virtualenv (%s) doesn't match "
                               "currently activated virtualenv (%s)."
                               % (options.venv, os.environ.get('VIRTUAL_ENV')))
                        sys.exit(3)
                else:
                    options.venv = os.environ.get('VIRTUAL_ENV')
                    print 'Using already activated environment %s' % options.venv
        level = 1 # Notify
        level += options.verbose
        level -= options.quiet
        level = Logger.level_for_integer(4-level)
        complete_log = []
        logger = Logger([(level, sys.stdout),
                         (Logger.DEBUG, complete_log.append)])
        if options.log_explicit_levels:
            logger.explicit_levels = True
        if options.venv:
            if options.verbose > 0:
                # The logger isn't setup yet
                print 'Running in environment %s' % options.venv
            site_packages=False
            if options.site_packages:
                site_packages=True
            restart_in_venv(options.venv, options.venv_base, site_packages,
                            complete_args)
            # restart_in_venv should actually never return, but for clarity...
            return
        ## FIXME: not sure if this sure come before or after venv restart
        if options.log:
            log_fp = open_logfile_append(options.log)
            logger.consumers.append((logger.DEBUG, log_fp))
        else:
            log_fp = None

        socket.setdefaulttimeout(options.timeout or None)

        setup_proxy_handler(options.proxy)

        exit = 0
        try:
            self.run(options, args)
        except (InstallationError, UninstallationError), e:
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = 1
        except:
            logger.fatal('Exception:\n%s' % format_exc())
            exit = 2

        if log_fp is not None:
            log_fp.close()
        if exit:
            log_fn = options.log_file
            text = '\n'.join(complete_log)
            logger.fatal('Storing complete log in %s' % log_fn)
            log_fp = open_logfile_append(log_fn)
            log_fp.write(text)
            log_fp.close()
        return exit

class HelpCommand(Command):
    name = 'help'
    usage = '%prog'
    summary = 'Show available commands'

    def run(self, options, args):
        if args:
            ## FIXME: handle errors better here
            command = args[0]
            if command not in _commands:
                raise InstallationError('No command with the name: %s' % command)
            command = _commands[command]
            command.parser.print_help()
            return
        parser.print_help()
        print
        print 'Commands available:'
        commands = list(set(_commands.values()))
        commands.sort(key=lambda x: x.name)
        for command in commands:
            if command.hidden:
                continue
            print '  %s: %s' % (command.name, command.summary)

HelpCommand()


class InstallCommand(Command):
    name = 'install'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'Install packages'
    bundle = False

    def __init__(self):
        super(InstallCommand, self).__init__()
        self.parser.add_option(
            '-e', '--editable',
            dest='editables',
            action='append',
            default=[],
            metavar='VCS+REPOS_URL[@REV]#egg=PACKAGE',
            help='Install a package directly from a checkout. Source will be checked '
            'out into src/PACKAGE (lower-case) and installed in-place (using '
            'setup.py develop). You can run this on an existing directory/checkout (like '
            'pip install -e src/mycheckout). This option may be provided multiple times. '
            'Possible values for VCS are: svn, git, hg and bzr.')
        self.parser.add_option(
            '-r', '--requirement',
            dest='requirements',
            action='append',
            default=[],
            metavar='FILENAME',
            help='Install all the packages listed in the given requirements file.  '
            'This option can be used multiple times.')
        self.parser.add_option(
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL to look for packages at')
        self.parser.add_option(
            '-i', '--index-url', '--pypi-url',
            dest='index_url',
            metavar='URL',
            default='http://pypi.python.org/simple',
            help='Base URL of Python Package Index (default %default)')
        self.parser.add_option(
            '--extra-index-url',
            dest='extra_index_urls',
            metavar='URL',
            action='append',
            default=[],
            help='Extra URLs of package indexes to use in addition to --index-url')
        self.parser.add_option(
            '--no-index',
            dest='no_index',
            action='store_true',
            default=False,
            help='Ignore package index (only looking at --find-links URLs instead)')

        self.parser.add_option(
            '-b', '--build', '--build-dir', '--build-directory',
            dest='build_dir',
            metavar='DIR',
            default=None,
            help='Unpack packages into DIR (default %s) and build from there' % build_prefix)
        self.parser.add_option(
            '-d', '--download', '--download-dir', '--download-directory',
            dest='download_dir',
            metavar='DIR',
            default=None,
            help='Download packages into DIR instead of installing them')
        self.parser.add_option(
            '--download-cache',
            dest='download_cache',
            metavar='DIR',
            default=None,
            help='Cache downloaded packages in DIR')
        self.parser.add_option(
            '--src', '--source', '--source-dir', '--source-directory',
            dest='src_dir',
            metavar='DIR',
            default=None,
            help='Check out --editable packages into DIR (default %s)' % src_prefix)

        self.parser.add_option(
            '-U', '--upgrade',
            dest='upgrade',
            action='store_true',
            help='Upgrade all packages to the newest available version')
        self.parser.add_option(
            '-I', '--ignore-installed',
            dest='ignore_installed',
            action='store_true',
            help='Ignore the installed packages (reinstalling instead)')
        self.parser.add_option(
            '--no-deps', '--no-dependencies',
            dest='ignore_dependencies',
            action='store_true',
            default=False,
            help='Ignore package dependencies')
        self.parser.add_option(
            '--no-install',
            dest='no_install',
            action='store_true',
            help="Download and unpack all packages, but don't actually install them")

        self.parser.add_option(
            '--install-option',
            dest='install_options',
            action='append',
            help="Extra arguments to be supplied to the setup.py install "
            "command (use like --install-option=\"--install-scripts=/usr/local/bin\").  "
            "Use multiple --install-option options to pass multiple options to setup.py install.  "
            "If you are using an option with a directory path, be sure to use absolute path.")

    def run(self, options, args):
        if not options.build_dir:
            options.build_dir = build_prefix
        if not options.src_dir:
            options.src_dir = src_prefix
        if options.download_dir:
            options.no_install = True
            options.ignore_installed = True
        else:
            options.build_dir = os.path.abspath(options.build_dir)
            options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []
        finder = PackageFinder(
            find_links=options.find_links,
            index_urls=index_urls)
        requirement_set = RequirementSet(
            build_dir=options.build_dir,
            src_dir=options.src_dir,
            download_dir=options.download_dir,
            download_cache=options.download_cache,
            upgrade=options.upgrade,
            ignore_installed=options.ignore_installed,
            ignore_dependencies=options.ignore_dependencies)
        for name in args:
            requirement_set.add_requirement(
                InstallRequirement.from_line(name, None))
        for name in options.editables:
            requirement_set.add_requirement(
                InstallRequirement.from_editable(name, default_vcs=options.default_vcs))
        for filename in options.requirements:
            for req in parse_requirements(filename, finder=finder, options=options):
                requirement_set.add_requirement(req)
        requirement_set.install_files(finder, force_root_egg_info=self.bundle)
        if not options.no_install and not self.bundle:
            requirement_set.install(install_options)
            installed = ' '.join([req.name for req in
                                  requirement_set.successfully_installed])
            if installed:
                logger.notify('Successfully installed %s' % installed)
        elif not self.bundle:
            downloaded = ' '.join([req.name for req in
                                   requirement_set.successfully_downloaded])
            if downloaded:
                logger.notify('Successfully downloaded %s' % downloaded)
        return requirement_set

InstallCommand()

class UninstallCommand(Command):
    name = 'uninstall'
    usage = '%prog [OPTIONS] PACKAGE_NAMES ...'
    summary = 'Uninstall packages'

    def __init__(self):
        super(UninstallCommand, self).__init__()
        self.parser.add_option(
            '-r', '--requirement',
            dest='requirements',
            action='append',
            default=[],
            metavar='FILENAME',
            help='Uninstall all the packages listed in the given requirements file.  '
            'This option can be used multiple times.')
        self.parser.add_option(
            '-y', '--yes',
            dest='yes',
            action='store_true',
            help="Don't ask for confirmation of uninstall deletions.")

    def run(self, options, args):
        requirement_set = RequirementSet(
            build_dir=None,
            src_dir=None,
            download_dir=None)
        for name in args:
            requirement_set.add_requirement(
                InstallRequirement.from_line(name))
        for filename in options.requirements:
            for req in parse_requirements(filename, options=options):
                requirement_set.add_requirement(req)
        requirement_set.uninstall(auto_confirm=options.yes)

UninstallCommand()

class BundleCommand(InstallCommand):
    name = 'bundle'
    usage = '%prog [OPTIONS] BUNDLE_NAME.pybundle PACKAGE_NAMES...'
    summary = 'Create pybundles (archives containing multiple packages)'
    bundle = True

    def __init__(self):
        super(BundleCommand, self).__init__()

    def run(self, options, args):
        if not args:
            raise InstallationError('You must give a bundle filename')
        if not options.build_dir:
            options.build_dir = backup_dir(build_prefix, '-bundle')
        if not options.src_dir:
            options.src_dir = backup_dir(src_prefix, '-bundle')
        # We have to get everything when creating a bundle:
        options.ignore_installed = True
        logger.notify('Putting temporary build files in %s and source/develop files in %s'
                      % (display_path(options.build_dir), display_path(options.src_dir)))
        bundle_filename = args[0]
        args = args[1:]
        requirement_set = super(BundleCommand, self).run(options, args)
        # FIXME: here it has to do something
        requirement_set.create_bundle(bundle_filename)
        logger.notify('Created bundle in %s' % bundle_filename)
        return requirement_set

BundleCommand()


class FreezeCommand(Command):
    name = 'freeze'
    usage = '%prog [OPTIONS]'
    summary = 'Output all currently installed packages (exact versions) to stdout'

    def __init__(self):
        super(FreezeCommand, self).__init__()
        self.parser.add_option(
            '-r', '--requirement',
            dest='requirement',
            action='store',
            default=None,
            metavar='FILENAME',
            help='Use the given requirements file as a hint about how to generate the new frozen requirements')
        self.parser.add_option(
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL for finding packages, which will be added to the frozen requirements file')

    def run(self, options, args):
        requirement = options.requirement
        find_links = options.find_links or []
        ## FIXME: Obviously this should be settable:
        find_tags = False
        skip_match = None

        skip_regex = options.skip_requirements_regex
        if skip_regex:
            skip_match = re.compile(skip_regex)

        logger.move_stdout_to_stderr()
        dependency_links = []

        f = sys.stdout

        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(dist.get_metadata_lines('dependency_links.txt'))
        for link in find_links:
            if '#egg=' in link:
                dependency_links.append(link)
        for link in find_links:
            f.write('-f %s\n' % link)
        installations = {}
        for dist in pkg_resources.working_set:
            if dist.key in ('setuptools', 'pip', 'python'):
                ## FIXME: also skip virtualenv?
                continue
            req = FrozenRequirement.from_dist(dist, dependency_links, find_tags=find_tags)
            installations[req.name] = req
        if requirement:
            req_f = open(requirement)
            for line in req_f:
                if not line.strip() or line.strip().startswith('#'):
                    f.write(line)
                    continue
                if skip_match and skip_match.search(line):
                    f.write(line)
                    continue
                elif line.startswith('-e') or line.startswith('--editable'):
                    if line.startswith('-e'):
                        line = line[2:].strip()
                    else:
                        line = line[len('--editable'):].strip().lstrip('=')
                    line_req = InstallRequirement.from_editable(line, default_vcs=options.default_vcs)
                elif (line.startswith('-r') or line.startswith('--requirement')
                      or line.startswith('-Z') or line.startswith('--always-unzip')):
                    logger.debug('Skipping line %r' % line.strip())
                    continue
                else:
                    line_req = InstallRequirement.from_line(line)
                if not line_req.name:
                    logger.notify("Skipping line because it's not clear what it would install: %s"
                                  % line.strip())
                    logger.notify("  (add #egg=PackageName to the URL to avoid this warning)")
                    continue
                if line_req.name not in installations:
                    logger.warn("Requirement file contains %s, but that package is not installed"
                                % line.strip())
                    continue
                f.write(str(installations[line_req.name]))
                del installations[line_req.name]
            f.write('## The following requirements were added by pip --freeze:\n')
        for installation in sorted(installations.values(), key=lambda x: x.name):
            f.write(str(installation))

FreezeCommand()

class ZipCommand(Command):
    name = 'zip'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'Zip individual packages'

    def __init__(self):
        super(ZipCommand, self).__init__()
        if self.name == 'zip':
            self.parser.add_option(
                '--unzip',
                action='store_true',
                dest='unzip',
                help='Unzip (rather than zip) a package')
        else:
            self.parser.add_option(
                '--zip',
                action='store_false',
                dest='unzip',
                default=True,
                help='Zip (rather than unzip) a package')
        self.parser.add_option(
            '--no-pyc',
            action='store_true',
            dest='no_pyc',
            help='Do not include .pyc files in zip files (useful on Google App Engine)')
        self.parser.add_option(
            '-l', '--list',
            action='store_true',
            dest='list',
            help='List the packages available, and their zip status')
        self.parser.add_option(
            '--sort-files',
            action='store_true',
            dest='sort_files',
            help='With --list, sort packages according to how many files they contain')
        self.parser.add_option(
            '--path',
            action='append',
            dest='paths',
            help='Restrict operations to the given paths (may include wildcards)')
        self.parser.add_option(
            '-n', '--simulate',
            action='store_true',
            help='Do not actually perform the zip/unzip operation')

    def paths(self):
        """All the entries of sys.path, possibly restricted by --path"""
        if not self.select_paths:
            return sys.path
        result = []
        match_any = set()
        for path in sys.path:
            path = os.path.normcase(os.path.abspath(path))
            for match in self.select_paths:
                match = os.path.normcase(os.path.abspath(match))
                if '*' in match:
                    if re.search(fnmatch.translate(match+'*'), path):
                        result.append(path)
                        match_any.add(match)
                        break
                else:
                    if path.startswith(match):
                        result.append(path)
                        match_any.add(match)
                        break
            else:
                logger.debug("Skipping path %s because it doesn't match %s"
                             % (path, ', '.join(self.select_paths)))
        for match in self.select_paths:
            if match not in match_any and '*' not in match:
                result.append(match)
                logger.debug("Adding path %s because it doesn't match anything already on sys.path"
                             % match)
        return result

    def run(self, options, args):
        self.select_paths = options.paths
        self.simulate = options.simulate
        if options.list:
            return self.list(options, args)
        if not args:
            raise InstallationError(
                'You must give at least one package to zip or unzip')
        packages = []
        for arg in args:
            module_name, filename = self.find_package(arg)
            if options.unzip and os.path.isdir(filename):
                raise InstallationError(
                    'The module %s (in %s) is not a zip file; cannot be unzipped'
                    % (module_name, filename))
            elif not options.unzip and not os.path.isdir(filename):
                raise InstallationError(
                    'The module %s (in %s) is not a directory; cannot be zipped'
                    % (module_name, filename))
            packages.append((module_name, filename))
        last_status = None
        for module_name, filename in packages:
            if options.unzip:
                last_status = self.unzip_package(module_name, filename)
            else:
                last_status = self.zip_package(module_name, filename, options.no_pyc)
        return last_status

    def unzip_package(self, module_name, filename):
        zip_filename = os.path.dirname(filename)
        if not os.path.isfile(zip_filename) and zipfile.is_zipfile(zip_filename):
            raise InstallationError(
                'Module %s (in %s) isn\'t located in a zip file in %s'
                % (module_name, filename, zip_filename))
        package_path = os.path.dirname(zip_filename)
        if not package_path in self.paths():
            logger.warn(
                'Unpacking %s into %s, but %s is not on sys.path'
                % (display_path(zip_filename), display_path(package_path),
                   display_path(package_path)))
        logger.notify('Unzipping %s (in %s)' % (module_name, display_path(zip_filename)))
        if self.simulate:
            logger.notify('Skipping remaining operations because of --simulate')
            return
        logger.indent += 2
        try:
            ## FIXME: this should be undoable:
            zip = zipfile.ZipFile(zip_filename)
            to_save = []
            for name in zip.namelist():
                if name.startswith('%s/' % module_name):
                    content = zip.read(name)
                    dest = os.path.join(package_path, name)
                    if not os.path.exists(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    if not content and dest.endswith('/'):
                        if not os.path.exists(dest):
                            os.makedirs(dest)
                    else:
                        f = open(dest, 'wb')
                        f.write(content)
                        f.close()
                else:
                    to_save.append((name, zip.read(name)))
            zip.close()
            if not to_save:
                logger.info('Removing now-empty zip file %s' % display_path(zip_filename))
                os.unlink(zip_filename)
                self.remove_filename_from_pth(zip_filename)
            else:
                logger.info('Removing entries in %s/ from zip file %s' % (module_name, display_path(zip_filename)))
                zip = zipfile.ZipFile(zip_filename, 'w')
                for name, content in to_save:
                    zip.writestr(name, content)
                zip.close()
        finally:
            logger.indent -= 2

    def zip_package(self, module_name, filename, no_pyc):
        orig_filename = filename
        logger.notify('Zip %s (in %s)' % (module_name, display_path(filename)))
        logger.indent += 2
        if filename.endswith('.egg'):
            dest_filename = filename
        else:
            dest_filename = filename + '.zip'
        try:
            ## FIXME: I think this needs to be undoable:
            if filename == dest_filename:
                filename = backup_dir(orig_filename)
                logger.notify('Moving %s aside to %s' % (orig_filename, filename))
                if not self.simulate:
                    shutil.move(orig_filename, filename)
            try:
                logger.info('Creating zip file in %s' % display_path(dest_filename))
                if not self.simulate:
                    zip = zipfile.ZipFile(dest_filename, 'w')
                    zip.writestr(module_name + '/', '')
                    for dirpath, dirnames, filenames in os.walk(filename):
                        if no_pyc:
                            filenames = [f for f in filenames
                                         if not f.lower().endswith('.pyc')]
                        for fns, is_dir in [(dirnames, True), (filenames, False)]:
                            for fn in fns:
                                full = os.path.join(dirpath, fn)
                                dest = os.path.join(module_name, dirpath[len(filename):].lstrip(os.path.sep), fn)
                                if is_dir:
                                    zip.writestr(dest+'/', '')
                                else:
                                    zip.write(full, dest)
                    zip.close()
                logger.info('Removing old directory %s' % display_path(filename))
                if not self.simulate:
                    shutil.rmtree(filename)
            except:
                ## FIXME: need to do an undo here
                raise
            ## FIXME: should also be undone:
            self.add_filename_to_pth(dest_filename)
        finally:
            logger.indent -= 2

    def remove_filename_from_pth(self, filename):
        for pth in self.pth_files():
            f = open(pth, 'r')
            lines = f.readlines()
            f.close()
            new_lines = [
                l for l in lines if l.strip() != filename]
            if lines != new_lines:
                logger.info('Removing reference to %s from .pth file %s'
                            % (display_path(filename), display_path(pth)))
                if not filter(None, new_lines):
                    logger.info('%s file would be empty: deleting' % display_path(pth))
                    if not self.simulate:
                        os.unlink(pth)
                else:
                    if not self.simulate:
                        f = open(pth, 'w')
                        f.writelines(new_lines)
                        f.close()
                return
        logger.warn('Cannot find a reference to %s in any .pth file' % display_path(filename))

    def add_filename_to_pth(self, filename):
        path = os.path.dirname(filename)
        dest = os.path.join(path, filename + '.pth')
        if path not in self.paths():
            logger.warn('Adding .pth file %s, but it is not on sys.path' % display_path(dest))
        if not self.simulate:
            if os.path.exists(dest):
                f = open(dest)
                lines = f.readlines()
                f.close()
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.append(filename+'\n')
            else:
                lines = [filename + '\n']
            f = open(dest, 'w')
            f.writelines(lines)
            f.close()

    def pth_files(self):
        for path in self.paths():
            if not os.path.exists(path) or not os.path.isdir(path):
                continue
            for filename in os.listdir(path):
                if filename.endswith('.pth'):
                    yield os.path.join(path, filename)

    def find_package(self, package):
        for path in self.paths():
            full = os.path.join(path, package)
            if os.path.exists(full):
                return package, full
            if not os.path.isdir(path) and zipfile.is_zipfile(path):
                zip = zipfile.ZipFile(path, 'r')
                try:
                    zip.read('%s/__init__.py' % package)
                except KeyError:
                    pass
                else:
                    zip.close()
                    return package, full
                zip.close()
        ## FIXME: need special error for package.py case:
        raise InstallationError(
            'No package with the name %s found' % package)

    def list(self, options, args):
        if args:
            raise InstallationError(
                'You cannot give an argument with --list')
        for path in sorted(self.paths()):
            if not os.path.exists(path):
                continue
            basename = os.path.basename(path.rstrip(os.path.sep))
            if os.path.isfile(path) and zipfile.is_zipfile(path):
                if os.path.dirname(path) not in self.paths():
                    logger.notify('Zipped egg: %s' % display_path(path))
                continue
            if (basename != 'site-packages'
                and not path.replace('\\', '/').endswith('lib/python')):
                continue
            logger.notify('In %s:' % display_path(path))
            logger.indent += 2
            zipped = []
            unzipped = []
            try:
                for filename in sorted(os.listdir(path)):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ('.pth', '.egg-info', '.egg-link'):
                        continue
                    if ext == '.py':
                        logger.info('Not displaying %s: not a package' % display_path(filename))
                        continue
                    full = os.path.join(path, filename)
                    if os.path.isdir(full):
                        unzipped.append((filename, self.count_package(full)))
                    elif zipfile.is_zipfile(full):
                        zipped.append(filename)
                    else:
                        logger.info('Unknown file: %s' % display_path(filename))
                if zipped:
                    logger.notify('Zipped packages:')
                    logger.indent += 2
                    try:
                        for filename in zipped:
                            logger.notify(filename)
                    finally:
                        logger.indent -= 2
                else:
                    logger.notify('No zipped packages.')
                if unzipped:
                    if options.sort_files:
                        unzipped.sort(key=lambda x: -x[1])
                    logger.notify('Unzipped packages:')
                    logger.indent += 2
                    try:
                        for filename, count in unzipped:
                            logger.notify('%s  (%i files)' % (filename, count))
                    finally:
                        logger.indent -= 2
                else:
                    logger.notify('No unzipped packages.')
            finally:
                logger.indent -= 2

    def count_package(self, path):
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            filenames = [f for f in filenames
                         if not f.lower().endswith('.pyc')]
            total += len(filenames)
        return total

ZipCommand()

class UnzipCommand(ZipCommand):
    name = 'unzip'
    summary = 'Unzip individual packages'

UnzipCommand()

BASE_COMPLETION = """
# pip %(shell)s completion start%(script)s# pip %(shell)s completion end
"""

COMPLETION_SCRIPTS = {
    'bash': """
_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 ) )
}
complete -o default -F _pip_completion pip
""", 'zsh': """
function _pip_completion {
  local words cword
  read -Ac words
  read -cn cword
  reply=( $( COMP_WORDS="$words[*]" \\ 
             COMP_CWORD=$(( cword-1 )) \\
             PIP_AUTO_COMPLETE=1 $words[1] ) )
}
compctl -K _pip_completion pip
"""
}

class CompletionCommand(Command):
    name = 'completion'
    summary = 'A helper command to be used for command completion'
    hidden = True

    def __init__(self):
        super(CompletionCommand, self).__init__()
        self.parser.add_option(
            '--bash', '-b',
            action='store_const',
            const='bash',
            dest='shell',
            help='Emit completion code for bash')
        self.parser.add_option(
            '--zsh', '-z',
            action='store_const',
            const='zsh',
            dest='shell',
            help='Emit completion code for zsh')

    def run(self, options, args):
        """Prints the completion code of the given shell"""
        if options.shell in ('bash', 'zsh'):
            script = COMPLETION_SCRIPTS.get(options.shell, '')
            print BASE_COMPLETION % {'script': script, 'shell': options.shell}
        else:
            print 'ERROR: You must pass --bash or --zsh'

CompletionCommand()

def autocomplete():
    """Command and option completion for the main option parser (and options)
    and its subcommands (and options).

    Enable by sourcing one of the completion shell scripts (bash or zsh).
    """
    # Don't complete if user hasn't sourced bash_completion file.
    if not os.environ.has_key('PIP_AUTO_COMPLETE'):
        return
    cwords = os.environ['COMP_WORDS'].split()[1:]
    cword = int(os.environ['COMP_CWORD'])
    try:
        current = cwords[cword-1]
    except IndexError:
        current = ''
    subcommands = [cmd for cmd, cls in _commands.items() if not cls.hidden]
    options = []
    # subcommand
    if cword == 1:
        # show options of main parser only when necessary
        if current.startswith('-') or current.startswith('--'):
            subcommands += [opt.get_opt_string()
                            for opt in parser.option_list
                            if opt.help != optparse.SUPPRESS_HELP]
        print ' '.join(filter(lambda x: x.startswith(current), subcommands))
    # subcommand options
    # special case: the 'help' subcommand has no options
    elif cwords[0] in subcommands and cwords[0] != 'help':
        subcommand = _commands.get(cwords[0])
        options += [(opt.get_opt_string(), opt.nargs)
                    for opt in subcommand.parser.option_list
                    if opt.help != optparse.SUPPRESS_HELP]
        # filter out previously specified options from available options
        prev_opts = [x.split('=')[0] for x in cwords[1:cword-1]]
        options = filter(lambda (x, v): x not in prev_opts, options)
        # filter options by current input
        options = [(k, v) for k, v in options if k.startswith(current)]
        for option in options:
            opt_label = option[0]
            # append '=' to options which require args
            if option[1]:
                opt_label += '='
            print opt_label
    sys.exit(1)

def main(initial_args=None):
    if initial_args is None:
        initial_args = sys.argv[1:]
    autocomplete()
    options, args = parser.parse_args(initial_args)
    if options.help and not args:
        args = ['help']
    if not args:
        parser.error('You must give a command (use "pip help" see a list of commands)')
    command = args[0].lower()
    ## FIXME: search for a command match?
    if command not in _commands:
        parser.error('No command by the name %(script)s %(arg)s\n  (maybe you meant "%(script)s install %(arg)s")'
                     % dict(script=os.path.basename(sys.argv[0]), arg=command))
    command = _commands[command]
    return command.main(initial_args, args[1:], options)

def get_proxy(proxystr=''):
    """Get the proxy given the option passed on the command line.  If an
    empty string is passed it looks at the HTTP_PROXY environment
    variable."""
    if not proxystr:
        proxystr = os.environ.get('HTTP_PROXY', '')
    if proxystr:
        if '@' in proxystr:
            user_password, server_port = proxystr.split('@', 1)
            if ':' in user_password:
                user, password = user_password.split(':', 1)
            else:
                user = user_password
                import getpass
                prompt = 'Password for %s@%s: ' % (user, server_port)
                password = urllib.quote(getpass.getpass(prompt))
            return '%s:%s@%s' % (user, password, server_port)
        else:
            return proxystr
    else:
        return None

def setup_proxy_handler(proxystr=''):
    """Set the proxy handler given the option passed on the command
    line.  If an empty string is passed it looks at the HTTP_PROXY
    environment variable.  """
    proxy = get_proxy(proxystr)
    if proxy:
        proxy_support = urllib2.ProxyHandler({"http": proxy, "ftp": proxy})
        opener = urllib2.build_opener(proxy_support, urllib2.CacheFTPHandler)
        urllib2.install_opener(opener)

def format_exc(exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()
    out = StringIO()
    traceback.print_exception(*exc_info, **dict(file=out))
    return out.getvalue()

def restart_in_venv(venv, base, site_packages, args):
    """
    Restart this script using the interpreter in the given virtual environment
    """
    if base and not os.path.isabs(venv) and not venv.startswith('~'):
        base = os.path.expanduser(base)
        # ensure we have an abs basepath at this point:
        #    a relative one makes no sense (or does it?)
        if os.path.isabs(base):
            venv = os.path.join(base, venv)

    if venv.startswith('~'):
        venv = os.path.expanduser(venv)

    if not os.path.exists(venv):
        try:
            import virtualenv
        except ImportError:
            print 'The virtual environment does not exist: %s' % venv
            print 'and virtualenv is not installed, so a new environment cannot be created'
            sys.exit(3)
        print 'Creating new virtualenv environment in %s' % venv
        virtualenv.logger = logger
        logger.indent += 2
        virtualenv.create_environment(venv, site_packages=site_packages)
    if sys.platform == 'win32':
        python = os.path.join(venv, 'Scripts', 'python.exe')
        # check for bin directory which is used in buildouts
        if not os.path.exists(python):
            python = os.path.join(venv, 'bin', 'python.exe')
    else:
        python = os.path.join(venv, 'bin', 'python')
    if not os.path.exists(python):
        python = venv
    if not os.path.exists(python):
        raise BadCommand('Cannot find virtual environment interpreter at %s' % python)
    base = os.path.dirname(os.path.dirname(python))
    file = __file__
    if file.endswith('.pyc'):
        file = file[:-1]
    proc = subprocess.Popen(
        [python, file] + args + [base, '___VENV_RESTART___'])
    proc.wait()
    sys.exit(proc.returncode)

class PackageFinder(object):
    """This finds packages.

    This is meant to match easy_install's technique for looking for
    packages, by reading pages and looking for appropriate links
    """

    failure_limit = 3

    def __init__(self, find_links, index_urls):
        self.find_links = find_links
        self.index_urls = index_urls
        self.dependency_links = []
        self.cache = PageCache()
        # These are boring links that have already been logged somehow:
        self.logged_links = set()

    def add_dependency_links(self, links):
        ## FIXME: this shouldn't be global list this, it should only
        ## apply to requirements of the package that specifies the
        ## dependency_links value
        ## FIXME: also, we should track comes_from (i.e., use Link)
        self.dependency_links.extend(links)

    def find_requirement(self, req, upgrade):
        url_name = req.url_name
        # Only check main index if index URL is given:
        main_index_url = None
        if self.index_urls:
            # Check that we have the url_name correctly spelled:
            main_index_url = Link(posixpath.join(self.index_urls[0], url_name))
            # This will also cache the page, so it's okay that we get it again later:
            page = self._get_page(main_index_url, req)
            if page is None:
                url_name = self._find_url_name(Link(self.index_urls[0]), url_name, req) or req.url_name
        def mkurl_pypi_url(url):
            loc =  posixpath.join(url, url_name)
            # For maximum compatibility with easy_install, ensure the path
            # ends in a trailing slash.  Although this isn't in the spec
            # (and PyPI can handle it without the slash) some other index
            # implementations might break if they relied on easy_install's behavior.
            if not loc.endswith('/'):
                loc = loc + '/'
            return loc
        if url_name is not None:
            locations = [
                mkurl_pypi_url(url)
                for url in self.index_urls] + self.find_links
        else:
            locations = list(self.find_links)
        locations.extend(self.dependency_links)
        for version in req.absolute_versions:
            if url_name is not None and main_index_url is not None:
                locations = [
                    posixpath.join(main_index_url.url, version)] + locations
        file_locations = []
        url_locations = []
        for url in locations:
            if url.startswith('file:'):
                fn = url_to_filename(url)
                if os.path.isdir(fn):
                    path = os.path.realpath(fn)
                    for item in os.listdir(path):
                        file_locations.append(
                            filename_to_url2(os.path.join(path, item)))
                elif os.path.isfile(fn):
                    file_locations.append(filename_to_url2(fn))
            else:
                url_locations.append(url)

        locations = [Link(url) for url in url_locations]
        logger.debug('URLs to search for versions for %s:' % req)
        for location in locations:
            logger.debug('* %s' % location)
        found_versions = []
        found_versions.extend(
            self._package_versions(
                [Link(url, '-f') for url in self.find_links], req.name.lower()))
        page_versions = []
        for page in self._get_pages(locations, req):
            logger.debug('Analyzing links from page %s' % page.url)
            logger.indent += 2
            try:
                page_versions.extend(self._package_versions(page.links, req.name.lower()))
            finally:
                logger.indent -= 2
        dependency_versions = list(self._package_versions(
            [Link(url) for url in self.dependency_links], req.name.lower()))
        if dependency_versions:
            logger.info('dependency_links found: %s' % ', '.join([link.url for parsed, link, version in dependency_versions]))
        file_versions = list(self._package_versions(
                [Link(url) for url in file_locations], req.name.lower()))
        if not found_versions and not page_versions and not dependency_versions and not file_versions:
            logger.fatal('Could not find any downloads that satisfy the requirement %s' % req)
            raise DistributionNotFound('No distributions at all found for %s' % req)
        if req.satisfied_by is not None:
            found_versions.append((req.satisfied_by.parsed_version, Inf, req.satisfied_by.version))
        if file_versions:
            file_versions.sort(reverse=True)
            logger.info('Local files found: %s' % ', '.join([url_to_filename(link.url) for parsed, link, version in file_versions]))
            found_versions = file_versions + found_versions
        all_versions = found_versions + page_versions + dependency_versions
        applicable_versions = []
        for (parsed_version, link, version) in all_versions:
            if version not in req.req:
                logger.info("Ignoring link %s, version %s doesn't match %s"
                            % (link, version, ','.join([''.join(s) for s in req.req.specs])))
                continue
            applicable_versions.append((link, version))
        applicable_versions = sorted(applicable_versions, key=operator.itemgetter(1),
            cmp=lambda x, y : cmp(pkg_resources.parse_version(y), pkg_resources.parse_version(x))
        )
        existing_applicable = bool([link for link, version in applicable_versions if link is Inf])
        if not upgrade and existing_applicable:
            if applicable_versions[0][1] is Inf:
                logger.info('Existing installed version (%s) is most up-to-date and satisfies requirement'
                            % req.satisfied_by.version)
            else:
                logger.info('Existing installed version (%s) satisfies requirement (most up-to-date version is %s)'
                            % (req.satisfied_by.version, applicable_versions[0][1]))
            return None
        if not applicable_versions:
            logger.fatal('Could not find a version that satisfies the requirement %s (from versions: %s)'
                         % (req, ', '.join([version for parsed_version, link, version in found_versions])))
            raise DistributionNotFound('No distributions matching the version for %s' % req)
        if applicable_versions[0][0] is Inf:
            # We have an existing version, and its the best version
            logger.info('Installed version (%s) is most up-to-date (past versions: %s)'
                        % (req.satisfied_by.version, ', '.join([version for link, version in applicable_versions[1:]]) or 'none'))
            return None
        if len(applicable_versions) > 1:
            logger.info('Using version %s (newest of versions: %s)' %
                        (applicable_versions[0][1], ', '.join([version for link, version in applicable_versions])))
        return applicable_versions[0][0]

    def _find_url_name(self, index_url, url_name, req):
        """Finds the true URL name of a package, when the given name isn't quite correct.
        This is usually used to implement case-insensitivity."""
        if not index_url.url.endswith('/'):
            # Vaguely part of the PyPI API... weird but true.
            ## FIXME: bad to modify this?
            index_url.url += '/'
        page = self._get_page(index_url, req)
        if page is None:
            logger.fatal('Cannot fetch index base URL %s' % index_url)
            return
        norm_name = normalize_name(req.url_name)
        for link in page.links:
            base = posixpath.basename(link.path.rstrip('/'))
            if norm_name == normalize_name(base):
                logger.notify('Real name of requirement %s is %s' % (url_name, base))
                return base
        return None

    def _get_pages(self, locations, req):
        """Yields (page, page_url) from the given locations, skipping
        locations that have errors, and adding download/homepage links"""
        pending_queue = Queue()
        for location in locations:
            pending_queue.put(location)
        done = []
        seen = set()
        threads = []
        for i in range(min(10, len(locations))):
            t = threading.Thread(target=self._get_queued_page, args=(req, pending_queue, done, seen))
            t.setDaemon(True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return done

    _log_lock = threading.Lock()

    def _get_queued_page(self, req, pending_queue, done, seen):
        while 1:
            try:
                location = pending_queue.get(False)
            except QueueEmpty:
                return
            if location in seen:
                continue
            seen.add(location)
            page = self._get_page(location, req)
            if page is None:
                continue
            done.append(page)
            for link in page.rel_links():
                pending_queue.put(link)

    _egg_fragment_re = re.compile(r'#egg=([^&]*)')
    _egg_info_re = re.compile(r'([a-z0-9_.]+)-([a-z0-9_.-]+)', re.I)
    _py_version_re = re.compile(r'-py([123]\.[0-9])$')

    def _sort_links(self, links):
        "Brings links in order, non-egg links first, egg links second"
        eggs, no_eggs = [], []
        for link in links:
            if link.egg_fragment:
                eggs.append(link)
            else:
                no_eggs.append(link)
        return no_eggs + eggs

    def _package_versions(self, links, search_name):
        seen_links = {}
        for link in self._sort_links(links):
            if link.url in seen_links:
                continue
            seen_links[link.url] = None
            if link.egg_fragment:
                egg_info = link.egg_fragment
            else:
                path = link.path
                egg_info, ext = link.splitext()
                if not ext:
                    if link not in self.logged_links:
                        logger.debug('Skipping link %s; not a file' % link)
                        self.logged_links.add(link)
                    continue
                if egg_info.endswith('.tar'):
                    # Special double-extension case:
                    egg_info = egg_info[:-4]
                    ext = '.tar' + ext
                if ext not in ('.tar.gz', '.tar.bz2', '.tar', '.tgz', '.zip'):
                    if link not in self.logged_links:
                        logger.debug('Skipping link %s; unknown archive format: %s' % (link, ext))
                        self.logged_links.add(link)
                    continue
            version = self._egg_info_matches(egg_info, search_name, link)
            if version is None:
                logger.debug('Skipping link %s; wrong project name (not %s)' % (link, search_name))
                continue
            match = self._py_version_re.search(version)
            if match:
                version = version[:match.start()]
                py_version = match.group(1)
                if py_version != sys.version[:3]:
                    logger.debug('Skipping %s because Python version is incorrect' % link)
                    continue
            logger.debug('Found link %s, version: %s' % (link, version))
            yield (pkg_resources.parse_version(version),
                   link,
                   version)

    def _egg_info_matches(self, egg_info, search_name, link):
        match = self._egg_info_re.search(egg_info)
        if not match:
            logger.debug('Could not parse version from link: %s' % link)
            return None
        name = match.group(0).lower()
        # To match the "safe" name that pkg_resources creates:
        name = name.replace('_', '-')
        if name.startswith(search_name.lower()):
            return match.group(0)[len(search_name):].lstrip('-')
        else:
            return None

    def _get_page(self, link, req):
        return HTMLPage.get_page(link, req, cache=self.cache)


class InstallRequirement(object):

    def __init__(self, req, comes_from, source_dir=None, editable=False,
                 url=None, update=True):
        if isinstance(req, basestring):
            req = pkg_resources.Requirement.parse(req)
        self.req = req
        self.comes_from = comes_from
        self.source_dir = source_dir
        self.editable = editable
        self.url = url
        self._egg_info_path = None
        # This holds the pkg_resources.Distribution object if this requirement
        # is already available:
        self.satisfied_by = None
        # This hold the pkg_resources.Distribution object if this requirement
        # conflicts with another installed distribution:
        self.conflicts_with = None
        self._temp_build_dir = None
        self._is_bundle = None
        # True if the editable should be updated:
        self.update = update
        # Set to True after successful installation
        self.install_succeeded = None
        # UninstallPathSet of uninstalled distribution (for possible rollback)
        self.uninstalled = None

    @classmethod
    def from_editable(cls, editable_req, comes_from=None, default_vcs=None):
        name, url = parse_editable(editable_req, default_vcs)
        if url.startswith('file:'):
            source_dir = url_to_filename(url)
        else:
            source_dir = None
        return cls(name, comes_from, source_dir=source_dir, editable=True, url=url)

    @classmethod
    def from_line(cls, name, comes_from=None):
        """Creates an InstallRequirement from a name, which might be a
        requirement, filename, or URL.
        """
        url = None
        name = name.strip()
        req = name
        if is_url(name):
            url = name
            ## FIXME: I think getting the requirement here is a bad idea:
            #req = get_requirement_from_url(url)
            req = None
        elif is_filename(name):
            if not os.path.exists(name):
                logger.warn('Requirement %r looks like a filename, but the file does not exist'
                            % name)
            url = filename_to_url(name)
            #req = get_requirement_from_url(url)
            req = None
        return cls(req, comes_from, url=url)

    def __str__(self):
        if self.req:
            s = str(self.req)
            if self.url:
                s += ' from %s' % self.url
        else:
            s = self.url
        if self.satisfied_by is not None:
            s += ' in %s' % display_path(self.satisfied_by.location)
        if self.comes_from:
            if isinstance(self.comes_from, basestring):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += ' (from %s)' % comes_from
        return s

    def from_path(self):
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            if isinstance(self.comes_from, basestring):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += '->' + comes_from
        return s

    def build_location(self, build_dir, unpack=True):
        if self._temp_build_dir is not None:
            return self._temp_build_dir
        if self.req is None:
            self._temp_build_dir = tempfile.mkdtemp('-build', 'pip-')
            self._ideal_build_dir = build_dir
            return self._temp_build_dir
        if self.editable:
            name = self.name.lower()
        else:
            name = self.name
        # FIXME: Is there a better place to create the build_dir? (hg and bzr need this)
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        return os.path.join(build_dir, name)

    def correct_build_location(self):
        """If the build location was a temporary directory, this will move it
        to a new more permanent location"""
        if self.source_dir is not None:
            return
        assert self.req is not None
        assert self._temp_build_dir
        old_location = self._temp_build_dir
        new_build_dir = self._ideal_build_dir
        del self._ideal_build_dir
        if self.editable:
            name = self.name.lower()
        else:
            name = self.name
        new_location = os.path.join(new_build_dir, name)
        if not os.path.exists(new_build_dir):
            logger.debug('Creating directory %s' % new_build_dir)
            os.makedirs(new_build_dir)
        if os.path.exists(new_location):
            raise InstallationError(
                'A package already exists in %s; please remove it to continue'
                % display_path(new_location))
        logger.debug('Moving package %s from %s to new location %s'
                     % (self, display_path(old_location), display_path(new_location)))
        shutil.move(old_location, new_location)
        self._temp_build_dir = new_location
        self.source_dir = new_location
        self._egg_info_path = None

    @property
    def name(self):
        if self.req is None:
            return None
        return self.req.project_name

    @property
    def url_name(self):
        if self.req is None:
            return None
        return urllib.quote(self.req.unsafe_name)

    @property
    def setup_py(self):
        return os.path.join(self.source_dir, 'setup.py')

    def run_egg_info(self, force_root_egg_info=False):
        assert self.source_dir
        if self.name:
            logger.notify('Running setup.py egg_info for package %s' % self.name)
        else:
            logger.notify('Running setup.py egg_info for package from %s' % self.url)
        logger.indent += 2
        try:
            script = self._run_setup_py
            script = script.replace('__SETUP_PY__', repr(self.setup_py))
            script = script.replace('__PKG_NAME__', repr(self.name))
            # We can't put the .egg-info files at the root, because then the source code will be mistaken
            # for an installed egg, causing problems
            if self.editable or force_root_egg_info:
                egg_base_option = []
            else:
                egg_info_dir = os.path.join(self.source_dir, 'pip-egg-info')
                if not os.path.exists(egg_info_dir):
                    os.makedirs(egg_info_dir)
                egg_base_option = ['--egg-base', 'pip-egg-info']
            call_subprocess(
                [sys.executable, '-c', script, 'egg_info'] + egg_base_option,
                cwd=self.source_dir, filter_stdout=self._filter_install, show_stdout=False,
                command_level=Logger.VERBOSE_DEBUG,
                command_desc='python setup.py egg_info')
        finally:
            logger.indent -= 2
        if not self.req:
            self.req = pkg_resources.Requirement.parse(self.pkg_info()['Name'])
            self.correct_build_location()

    ## FIXME: This is a lame hack, entirely for PasteScript which has
    ## a self-provided entry point that causes this awkwardness
    _run_setup_py = """
__file__ = __SETUP_PY__
from setuptools.command import egg_info
def replacement_run(self):
    self.mkpath(self.egg_info)
    installer = self.distribution.fetch_build_egg
    for ep in egg_info.iter_entry_points('egg_info.writers'):
        # require=False is the change we're making:
        writer = ep.load(require=False)
        if writer:
            writer(self, ep.name, egg_info.os.path.join(self.egg_info,ep.name))
    self.find_sources()
egg_info.egg_info.run = replacement_run
execfile(__file__)
"""

    def egg_info_data(self, filename):
        if self.satisfied_by is not None:
            if not self.satisfied_by.has_metadata(filename):
                return None
            return self.satisfied_by.get_metadata(filename)
        assert self.source_dir
        filename = self.egg_info_path(filename)
        if not os.path.exists(filename):
            return None
        fp = open(filename, 'r')
        data = fp.read()
        fp.close()
        return data

    def egg_info_path(self, filename):
        if self._egg_info_path is None:
            if self.editable:
                base = self.source_dir
            else:
                base = os.path.join(self.source_dir, 'pip-egg-info')
            filenames = os.listdir(base)
            if self.editable:
                filenames = []
                for root, dirs, files in os.walk(base):
                    for dir in vcs.dirnames:
                        if dir in dirs:
                            dirs.remove(dir)
                    filenames.extend([os.path.join(root, dir)
                                     for dir in dirs])
                filenames = [f for f in filenames if f.endswith('.egg-info')]
            assert filenames, "No files/directories in %s (from %s)" % (base, filename)
            assert len(filenames) == 1, "Unexpected files/directories in %s: %s" % (base, ' '.join(filenames))
            self._egg_info_path = os.path.join(base, filenames[0])
        return os.path.join(self._egg_info_path, filename)

    def egg_info_lines(self, filename):
        data = self.egg_info_data(filename)
        if not data:
            return []
        result = []
        for line in data.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            result.append(line)
        return result

    def pkg_info(self):
        p = FeedParser()
        data = self.egg_info_data('PKG-INFO')
        if not data:
            logger.warn('No PKG-INFO file found in %s' % display_path(self.egg_info_path('PKG-INFO')))
        p.feed(data or '')
        return p.close()

    @property
    def dependency_links(self):
        return self.egg_info_lines('dependency_links.txt')

    _requirements_section_re = re.compile(r'\[(.*?)\]')

    def requirements(self, extras=()):
        in_extra = None
        for line in self.egg_info_lines('requires.txt'):
            match = self._requirements_section_re.match(line)
            if match:
                in_extra = match.group(1)
                continue
            if in_extra and in_extra not in extras:
                # Skip requirement for an extra we aren't requiring
                continue
            yield line

    @property
    def absolute_versions(self):
        for qualifier, version in self.req.specs:
            if qualifier == '==':
                yield version

    @property
    def installed_version(self):
        return self.pkg_info()['version']

    def assert_source_matches_version(self):
        assert self.source_dir
        if self.comes_from is None:
            # We don't check the versions of things explicitly installed.
            # This makes, e.g., "pip Package==dev" possible
            return
        version = self.installed_version
        if version not in self.req:
            logger.fatal(
                'Source in %s has the version %s, which does not match the requirement %s'
                % (display_path(self.source_dir), version, self))
            raise InstallationError(
                'Source in %s has version %s that conflicts with %s'
                % (display_path(self.source_dir), version, self))
        else:
            logger.debug('Source in %s has version %s, which satisfies requirement %s'
                         % (display_path(self.source_dir), version, self))

    def update_editable(self, obtain=True):
        if not self.url:
            logger.info("Cannot update repository at %s; repository location is unknown" % self.source_dir)
            return
        assert self.editable
        assert self.source_dir
        if self.url.startswith('file:'):
            # Static paths don't get updated
            return
        assert '+' in self.url, "bad url: %r" % self.url
        if not self.update:
            return
        vc_type, url = self.url.split('+', 1)
        backend = vcs.get_backend(vc_type)
        if backend:
            vcs_backend = backend(self.url)
            if obtain:
                vcs_backend.obtain(self.source_dir)
            else:
                vcs_backend.export(self.source_dir)
        else:
            assert 0, (
                'Unexpected version control type (in %s): %s'
                % (self.url, vc_type))

    def uninstall(self, auto_confirm=False):
        """
        Uninstall the distribution currently satisfying this requirement.

        Prompts before removing or modifying files unless
        ``auto_confirm`` is True.

        Refuses to delete or modify files outside of ``sys.prefix`` -
        thus uninstallation within a virtual environment can only
        modify that virtual environment, even if the virtualenv is
        linked to global site-packages.

        """
        if not self.check_if_exists():
            raise UninstallationError("Cannot uninstall requirement %s, not installed" % (self.name,))
        dist = self.satisfied_by or self.conflicts_with
        paths_to_remove = UninstallPathSet(dist, sys.prefix)

        pip_egg_info_path = os.path.join(dist.location,
                                         dist.egg_name()) + '.egg-info'
        easy_install_egg = dist.egg_name() + '.egg'
        # This won't find a globally-installed develop egg if
        # we're in a virtualenv.
        # (There doesn't seem to be any metadata in the
        # Distribution object for a develop egg that points back
        # to its .egg-link and easy-install.pth files).  That's
        # OK, because we restrict ourselves to making changes
        # within sys.prefix anyway.
        develop_egg_link = os.path.join(site_packages,
                                        dist.project_name) + '.egg-link'
        if os.path.exists(pip_egg_info_path):
            # package installed by pip
            paths_to_remove.add(pip_egg_info_path)
            if dist.has_metadata('installed-files.txt'):
                for installed_file in dist.get_metadata('installed-files.txt').splitlines():
                    path = os.path.normpath(os.path.join(pip_egg_info_path, installed_file))
                    if os.path.exists(path):
                        paths_to_remove.add(path)
            if dist.has_metadata('top_level.txt'):
                for top_level_pkg in [p for p
                                      in dist.get_metadata('top_level.txt').splitlines()
                                      if p]:
                    path = os.path.join(dist.location, top_level_pkg)
                    if os.path.exists(path):
                        paths_to_remove.add(path)
                    elif os.path.exists(path + '.py'):
                        paths_to_remove.add(path + '.py')
                        if os.path.exists(path + '.pyc'):
                            paths_to_remove.add(path + '.pyc')

        elif dist.location.endswith(easy_install_egg):
            # package installed by easy_install
            paths_to_remove.add(dist.location)
            easy_install_pth = os.path.join(os.path.dirname(dist.location),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, './' + easy_install_egg)

        elif os.path.isfile(develop_egg_link):
            # develop egg
            fh = open(develop_egg_link, 'r')
            link_pointer = os.path.normcase(fh.readline().strip())
            fh.close()
            assert (link_pointer == dist.location), 'Egg-link %s does not match installed location of %s (at %s)' % (link_pointer, self.name, dist.location)
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(os.path.dirname(develop_egg_link),
                                            'easy-install.pth')
            paths_to_remove.add_pth(easy_install_pth, dist.location)
            # fix location (so we can uninstall links to sources outside venv)
            paths_to_remove.location = develop_egg_link

        # find distutils scripts= scripts
        if dist.has_metadata('scripts') and dist.metadata_isdir('scripts'):
            for script in dist.metadata_listdir('scripts'):
                paths_to_remove.add(os.path.join(bin_py, script))
                if sys.platform == 'win32':
                    paths_to_remove.add(os.path.join(bin_py, script) + '.bat')

        # find console_scripts
        if dist.has_metadata('entry_points.txt'):
            config = ConfigParser.SafeConfigParser()
            config.readfp(FakeFile(dist.get_metadata_lines('entry_points.txt')))
            if config.has_section('console_scripts'):
                for name, value in config.items('console_scripts'):
                    paths_to_remove.add(os.path.join(bin_py, name))
                    if sys.platform == 'win32':
                        paths_to_remove.add(os.path.join(bin_py, name) + '.exe')
                        paths_to_remove.add(os.path.join(bin_py, name) + '-script.py')

        paths_to_remove.remove(auto_confirm)
        self.uninstalled = paths_to_remove

    def rollback_uninstall(self):
        if self.uninstalled:
            self.uninstalled.rollback()
        else:
            logger.error("Can't rollback %s, nothing uninstalled."
                         % (self.project_name,))

    def archive(self, build_dir):
        assert self.source_dir
        create_archive = True
        archive_name = '%s-%s.zip' % (self.name, self.installed_version)
        archive_path = os.path.join(build_dir, archive_name)
        if os.path.exists(archive_path):
            response = ask('The file %s exists. (i)gnore, (w)ipe, (b)ackup '
                           % display_path(archive_path), ('i', 'w', 'b'))
            if response == 'i':
                create_archive = False
            elif response == 'w':
                logger.warn('Deleting %s' % display_path(archive_path))
                os.remove(archive_path)
            elif response == 'b':
                dest_file = backup_dir(archive_path)
                logger.warn('Backing up %s to %s'
                            % (display_path(archive_path), display_path(dest_file)))
                shutil.move(archive_path, dest_file)
        if create_archive:
            zip = zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED)
            dir = os.path.normcase(os.path.abspath(self.source_dir))
            for dirpath, dirnames, filenames in os.walk(dir):
                if 'pip-egg-info' in dirnames:
                    dirnames.remove('pip-egg-info')
                for dirname in dirnames:
                    dirname = os.path.join(dirpath, dirname)
                    name = self._clean_zip_name(dirname, dir)
                    zipdir = zipfile.ZipInfo(self.name + '/' + name + '/')
                    zipdir.external_attr = 0755 << 16L
                    zip.writestr(zipdir, '')
                for filename in filenames:
                    if filename == 'pip-delete-this-directory.txt':
                        continue
                    filename = os.path.join(dirpath, filename)
                    name = self._clean_zip_name(filename, dir)
                    zip.write(filename, self.name + '/' + name)
            zip.close()
            logger.indent -= 2
            logger.notify('Saved %s' % display_path(archive_path))

    def _clean_zip_name(self, name, prefix):
        assert name.startswith(prefix+'/'), (
            "name %r doesn't start with prefix %r" % (name, prefix))
        name = name[len(prefix)+1:]
        name = name.replace(os.path.sep, '/')
        return name

    def install(self, install_options):
        if self.editable:
            self.install_editable()
            return
        temp_location = tempfile.mkdtemp('-record', 'pip-')
        record_filename = os.path.join(temp_location, 'install-record.txt')
        ## FIXME: I'm not sure if this is a reasonable location; probably not
        ## but we can't put it in the default location, as that is a virtualenv symlink that isn't writable
        header_dir = os.path.join(os.path.dirname(os.path.dirname(self.source_dir)), 'lib', 'include')
        logger.notify('Running setup.py install for %s' % self.name)
        logger.indent += 2
        try:
            call_subprocess(
                [sys.executable, '-c',
                 "import setuptools; __file__=%r; execfile(%r)" % (self.setup_py, self.setup_py),
                 'install', '--single-version-externally-managed', '--record', record_filename,
                 '--install-headers', header_dir] + install_options,
                cwd=self.source_dir, filter_stdout=self._filter_install, show_stdout=False)
        finally:
            logger.indent -= 2
        self.install_succeeded = True
        f = open(record_filename)
        for line in f:
            line = line.strip()
            if line.endswith('.egg-info'):
                egg_info_dir = line
                break
        else:
            logger.warn('Could not find .egg-info directory in install record for %s' % self)
            ## FIXME: put the record somewhere
            return
        f.close()
        new_lines = []
        f = open(record_filename)
        for line in f:
            filename = line.strip()
            if os.path.isdir(filename):
                filename += os.path.sep
            new_lines.append(make_path_relative(filename, egg_info_dir))
        f.close()
        f = open(os.path.join(egg_info_dir, 'installed-files.txt'), 'w')
        f.write('\n'.join(new_lines)+'\n')
        f.close()

    def remove_temporary_source(self):
        """Remove the source files from this requirement, if they are marked
        for deletion"""
        if self.is_bundle or os.path.exists(self.delete_marker_filename):
            logger.info('Removing source in %s' % self.source_dir)
            if self.source_dir:
                shutil.rmtree(self.source_dir, ignore_errors=True, onerror=rmtree_errorhandler)
            self.source_dir = None
            if self._temp_build_dir and os.path.exists(self._temp_build_dir):
                shutil.rmtree(self._temp_build_dir, ignore_errors=True, onerror=rmtree_errorhandler)
            self._temp_build_dir = None

    def install_editable(self):
        logger.notify('Running setup.py develop for %s' % self.name)
        logger.indent += 2
        try:
            ## FIXME: should we do --install-headers here too?
            call_subprocess(
                [sys.executable, '-c',
                 "import setuptools; __file__=%r; execfile(%r)" % (self.setup_py, self.setup_py),
                 'develop', '--no-deps'], cwd=self.source_dir, filter_stdout=self._filter_install,
                show_stdout=False)
        finally:
            logger.indent -= 2
        self.install_succeeded = True

    def _filter_install(self, line):
        level = Logger.NOTIFY
        for regex in [r'^running .*', r'^writing .*', '^creating .*', '^[Cc]opying .*',
                      r'^reading .*', r"^removing .*\.egg-info' \(and everything under it\)$",
                      r'^byte-compiling ',
                      # Not sure what this warning is, but it seems harmless:
                      r"^warning: manifest_maker: standard file '-c' not found$"]:
            if re.search(regex, line.strip()):
                level = Logger.INFO
                break
        return (level, line)

    def check_if_exists(self):
        """Find an installed distribution that satisfies or conflicts
        with this requirement, and set self.satisfied_by or
        self.conflicts_with appropriately."""
        if self.req is None:
            return False
        try:
            self.satisfied_by = pkg_resources.get_distribution(self.req)
        except pkg_resources.DistributionNotFound:
            return False
        except pkg_resources.VersionConflict:
            self.conflicts_with = pkg_resources.get_distribution(self.req.project_name)
        return True

    @property
    def is_bundle(self):
        if self._is_bundle is not None:
            return self._is_bundle
        base = self._temp_build_dir
        if not base:
            ## FIXME: this doesn't seem right:
            return False
        self._is_bundle = (os.path.exists(os.path.join(base, 'pip-manifest.txt'))
                           or os.path.exists(os.path.join(base, 'pyinstall-manifest.txt')))
        return self._is_bundle

    def bundle_requirements(self):
        for dest_dir in self._bundle_editable_dirs:
            package = os.path.basename(dest_dir)
            ## FIXME: svnism:
            for vcs_backend in vcs.backends:
                url = rev = None
                vcs_bundle_file = os.path.join(
                    dest_dir, vcs_backend.bundle_file)
                if os.path.exists(vcs_bundle_file):
                    vc_type = vcs_backend.name
                    fp = open(vcs_bundle_file)
                    content = fp.read()
                    fp.close()
                    url, rev = vcs_backend().parse_vcs_bundle_file(content)
                    break
            if url:
                url = '%s+%s@%s' % (vc_type, url, rev)
            else:
                url = None
            yield InstallRequirement(
                package, self, editable=True, url=url,
                update=False, source_dir=dest_dir)
        for dest_dir in self._bundle_build_dirs:
            package = os.path.basename(dest_dir)
            yield InstallRequirement(
                package, self,
                source_dir=dest_dir)

    def move_bundle_files(self, dest_build_dir, dest_src_dir):
        base = self._temp_build_dir
        assert base
        src_dir = os.path.join(base, 'src')
        build_dir = os.path.join(base, 'build')
        bundle_build_dirs = []
        bundle_editable_dirs = []
        for source_dir, dest_dir, dir_collection in [
            (src_dir, dest_src_dir, bundle_editable_dirs),
            (build_dir, dest_build_dir, bundle_build_dirs)]:
            if os.path.exists(source_dir):
                for dirname in os.listdir(source_dir):
                    dest = os.path.join(dest_dir, dirname)
                    dir_collection.append(dest)
                    if os.path.exists(dest):
                        logger.warn('The directory %s (containing package %s) already exists; cannot move source from bundle %s'
                                    % (dest, dirname, self))
                        continue
                    if not os.path.exists(dest_dir):
                        logger.info('Creating directory %s' % dest_dir)
                        os.makedirs(dest_dir)
                    shutil.move(os.path.join(source_dir, dirname), dest)
                if not os.listdir(source_dir):
                    os.rmdir(source_dir)
        self._temp_build_dir = None
        self._bundle_build_dirs = bundle_build_dirs
        self._bundle_editable_dirs = bundle_editable_dirs

    @property
    def delete_marker_filename(self):
        assert self.source_dir
        return os.path.join(self.source_dir, 'pip-delete-this-directory.txt')

DELETE_MARKER_MESSAGE = '''\
This file is placed here by pip to indicate the source was put
here by pip.

Once this package is successfully installed this source code will be
deleted (unless you remove this file).
'''

class RequirementSet(object):

    def __init__(self, build_dir, src_dir, download_dir, download_cache=None,
                 upgrade=False, ignore_installed=False,
                 ignore_dependencies=False):
        self.build_dir = build_dir
        self.src_dir = src_dir
        self.download_dir = download_dir
        self.download_cache = download_cache
        self.upgrade = upgrade
        self.ignore_installed = ignore_installed
        self.requirements = {}
        # Mapping of alias: real_name
        self.requirement_aliases = {}
        self.unnamed_requirements = []
        self.ignore_dependencies = ignore_dependencies
        self.successfully_downloaded = []
        self.successfully_installed = []

    def __str__(self):
        reqs = [req for req in self.requirements.values()
                if not req.comes_from]
        reqs.sort(key=lambda req: req.name.lower())
        return ' '.join([str(req.req) for req in reqs])

    def add_requirement(self, install_req):
        name = install_req.name
        if not name:
            self.unnamed_requirements.append(install_req)
        else:
            if self.has_requirement(name):
                raise InstallationError(
                    'Double requirement given: %s (aready in %s, name=%r)'
                    % (install_req, self.get_requirement(name), name))
            self.requirements[name] = install_req
            ## FIXME: what about other normalizations?  E.g., _ vs. -?
            if name.lower() != name:
                self.requirement_aliases[name.lower()] = name

    def has_requirement(self, project_name):
        for name in project_name, project_name.lower():
            if name in self.requirements or name in self.requirement_aliases:
                return True
        return False

    @property
    def is_download(self):
        if self.download_dir:
            self.download_dir = os.path.expanduser(self.download_dir)
            if os.path.exists(self.download_dir):
                return True
            else:
                logger.fatal('Could not find download directory')
                raise InstallationError(
                    "Could not find or access download directory '%s'"
                    % display_path(self.download_dir))
        return False

    def get_requirement(self, project_name):
        for name in project_name, project_name.lower():
            if name in self.requirements:
                return self.requirements[name]
            if name in self.requirement_aliases:
                return self.requirements[self.requirement_aliases[name]]
        raise KeyError("No project with the name %r" % project_name)

    def uninstall(self, auto_confirm=False):
        for req in self.requirements.values():
            req.uninstall(auto_confirm=auto_confirm)

    def install_files(self, finder, force_root_egg_info=False):
        unnamed = list(self.unnamed_requirements)
        reqs = self.requirements.values()
        while reqs or unnamed:
            if unnamed:
                req_to_install = unnamed.pop(0)
            else:
                req_to_install = reqs.pop(0)
            install = True
            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()
                if req_to_install.satisfied_by:
                    if self.upgrade:
                        req_to_install.conflicts_with = req_to_install.satisfied_by
                        req_to_install.satisfied_by = None
                    else:
                        install = False
                if req_to_install.satisfied_by:
                    logger.notify('Requirement already satisfied '
                                  '(use --upgrade to upgrade): %s'
                                  % req_to_install)
            if req_to_install.editable:
                logger.notify('Obtaining %s' % req_to_install)
            elif install:
                if req_to_install.url and req_to_install.url.lower().startswith('file:'):
                    logger.notify('Unpacking %s' % display_path(url_to_filename(req_to_install.url)))
                else:
                    logger.notify('Downloading/unpacking %s' % req_to_install)
            logger.indent += 2
            is_bundle = False
            try:
                if req_to_install.editable:
                    if req_to_install.source_dir is None:
                        location = req_to_install.build_location(self.src_dir)
                        req_to_install.source_dir = location
                    else:
                        location = req_to_install.source_dir
                    if not os.path.exists(self.build_dir):
                        os.makedirs(self.build_dir)
                    req_to_install.update_editable(not self.is_download)
                    if self.is_download:
                        req_to_install.run_egg_info()
                        req_to_install.archive(self.download_dir)
                    else:
                        req_to_install.run_egg_info()
                elif install:
                    location = req_to_install.build_location(self.build_dir, not self.is_download)
                    ## FIXME: is the existance of the checkout good enough to use it?  I don't think so.
                    unpack = True
                    if not os.path.exists(os.path.join(location, 'setup.py')):
                        ## FIXME: this won't upgrade when there's an existing package unpacked in `location`
                        if req_to_install.url is None:
                            url = finder.find_requirement(req_to_install, upgrade=self.upgrade)
                        else:
                            ## FIXME: should req_to_install.url already be a link?
                            url = Link(req_to_install.url)
                            assert url
                        if url:
                            try:
                                self.unpack_url(url, location, self.is_download)
                            except urllib2.HTTPError, e:
                                logger.fatal('Could not install requirement %s because of error %s'
                                             % (req_to_install, e))
                                raise InstallationError(
                                    'Could not install requirement %s because of HTTP error %s for URL %s'
                                    % (req_to_install, e, url))
                        else:
                            unpack = False
                    if unpack:
                        is_bundle = req_to_install.is_bundle
                        url = None
                        if is_bundle:
                            req_to_install.move_bundle_files(self.build_dir, self.src_dir)
                            for subreq in req_to_install.bundle_requirements():
                                reqs.append(subreq)
                                self.add_requirement(subreq)
                        elif self.is_download:
                            req_to_install.source_dir = location
                            if url and url.scheme in vcs.all_schemes:
                                req_to_install.run_egg_info()
                                req_to_install.archive(self.download_dir)
                        else:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if force_root_egg_info:
                                # We need to run this to make sure that the .egg-info/
                                # directory is created for packing in the bundle
                                req_to_install.run_egg_info(force_root_egg_info=True)
                            req_to_install.assert_source_matches_version()
                            f = open(req_to_install.delete_marker_filename, 'w')
                            f.write(DELETE_MARKER_MESSAGE)
                            f.close()
                if not is_bundle and not self.is_download:
                    ## FIXME: shouldn't be globally added:
                    finder.add_dependency_links(req_to_install.dependency_links)
                    ## FIXME: add extras in here:
                    if not self.ignore_dependencies:
                        for req in req_to_install.requirements():
                            try:
                                name = pkg_resources.Requirement.parse(req).project_name
                            except ValueError, e:
                                ## FIXME: proper warning
                                logger.error('Invalid requirement: %r (%s) in requirement %s' % (req, e, req_to_install))
                                continue
                            if self.has_requirement(name):
                                ## FIXME: check for conflict
                                continue
                            subreq = InstallRequirement(req, req_to_install)
                            reqs.append(subreq)
                            self.add_requirement(subreq)
                    if req_to_install.name not in self.requirements:
                        self.requirements[req_to_install.name] = req_to_install
                else:
                    req_to_install.remove_temporary_source()
                if install:
                    self.successfully_downloaded.append(req_to_install)
            finally:
                logger.indent -= 2

    def unpack_url(self, link, location, only_download=False):
        if only_download:
            location = self.download_dir
        for backend in vcs.backends:
            if link.scheme in backend.schemes:
                vcs_backend = backend(link.url)
                if only_download:
                    vcs_backend.export(location)
                else:
                    vcs_backend.unpack(location)
                return
        dir = tempfile.mkdtemp()
        if link.url.lower().startswith('file:'):
            source = url_to_filename(link.url)
            content_type = mimetypes.guess_type(source)[0]
            self.unpack_file(source, location, content_type, link)
            return
        md5_hash = link.md5_hash
        target_url = link.url.split('#', 1)[0]
        target_file = None
        if self.download_cache:
            if not os.path.isdir(self.download_cache):
                logger.indent -= 2
                logger.notify('Creating supposed download cache at %s' % self.download_cache)
                logger.indent += 2
                os.makedirs(self.download_cache)
            target_file = os.path.join(self.download_cache,
                                       urllib.quote(target_url, ''))
        if (target_file and os.path.exists(target_file)
            and os.path.exists(target_file+'.content-type')):
            fp = open(target_file+'.content-type')
            content_type = fp.read().strip()
            fp.close()
            if md5_hash:
                download_hash = md5()
                fp = open(target_file, 'rb')
                while 1:
                    chunk = fp.read(4096)
                    if not chunk:
                        break
                    download_hash.update(chunk)
                fp.close()
            temp_location = target_file
            logger.notify('Using download cache from %s' % target_file)
        else:
            try:
                resp = urllib2.urlopen(target_url)
            except urllib2.HTTPError, e:
                logger.fatal("HTTP error %s while getting %s" % (e.code, link))
                raise
            except IOError, e:
                # Typically an FTP error
                logger.fatal("Error %s while getting %s" % (e, link))
                raise
            content_type = resp.info()['content-type']
            filename = link.filename
            ext = splitext(filename)[1]
            if not ext:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    filename += ext
            if not ext and link.url != resp.geturl():
                ext = os.path.splitext(resp.geturl())[1]
                if ext:
                    filename += ext
            temp_location = os.path.join(dir, filename)
            fp = open(temp_location, 'wb')
            if md5_hash:
                download_hash = md5()
            try:
                total_length = int(resp.info()['content-length'])
            except (ValueError, KeyError):
                total_length = 0
            downloaded = 0
            show_progress = total_length > 40*1000 or not total_length
            show_url = link.show_url
            try:
                if show_progress:
                    ## FIXME: the URL can get really long in this message:
                    if total_length:
                        logger.start_progress('Downloading %s (%s): ' % (show_url, format_size(total_length)))
                    else:
                        logger.start_progress('Downloading %s (unknown size): ' % show_url)
                else:
                    logger.notify('Downloading %s' % show_url)
                logger.debug('Downloading from URL %s' % link)
                while 1:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if show_progress:
                        if not total_length:
                            logger.show_progress('%s' % format_size(downloaded))
                        else:
                            logger.show_progress('%3i%%  %s' % (100*downloaded/total_length, format_size(downloaded)))
                    if md5_hash:
                        download_hash.update(chunk)
                    fp.write(chunk)
                fp.close()
            finally:
                if show_progress:
                    logger.end_progress('%s downloaded' % format_size(downloaded))
        if md5_hash:
            download_hash = download_hash.hexdigest()
            if download_hash != md5_hash:
                logger.fatal("MD5 hash of the package %s (%s) doesn't match the expected hash %s!"
                             % (link, download_hash, md5_hash))
                raise InstallationError('Bad MD5 hash for package %s' % link)
        if only_download:
            self.copy_file(temp_location, location, content_type, link)
        else:
            self.unpack_file(temp_location, location, content_type, link)
        if target_file and target_file != temp_location:
            logger.notify('Storing download in cache at %s' % display_path(target_file))
            shutil.copyfile(temp_location, target_file)
            fp = open(target_file+'.content-type', 'w')
            fp.write(content_type)
            fp.close()
            os.unlink(temp_location)
        if target_file is None:
            os.unlink(temp_location)

    def copy_file(self, filename, location, content_type, link):
        copy = True
        download_location = os.path.join(location, link.filename)
        if os.path.exists(download_location):
            response = ask('The file %s exists. (i)gnore, (w)ipe, (b)ackup '
                           % display_path(download_location), ('i', 'w', 'b'))
            if response == 'i':
                copy = False
            elif response == 'w':
                logger.warn('Deleting %s' % display_path(download_location))
                os.remove(download_location)
            elif response == 'b':
                dest_file = backup_dir(download_location)
                logger.warn('Backing up %s to %s'
                            % (display_path(download_location), display_path(dest_file)))
                shutil.move(download_location, dest_file)
        if copy:
            shutil.copy(filename, download_location)
            logger.indent -= 2
            logger.notify('Saved %s' % display_path(download_location))

    def unpack_file(self, filename, location, content_type, link):
        if (content_type == 'application/zip'
            or filename.endswith('.zip')
            or filename.endswith('.pybundle')
            or zipfile.is_zipfile(filename)):
            self.unzip_file(filename, location, flatten=not filename.endswith('.pybundle'))
        elif (content_type == 'application/x-gzip'
              or tarfile.is_tarfile(filename)
              or splitext(filename)[1].lower() in ('.tar', '.tar.gz', '.tar.bz2', '.tgz', '.tbz')):
            self.untar_file(filename, location)
        elif (content_type and content_type.startswith('text/html')
              and is_svn_page(file_contents(filename))):
            # We don't really care about this
            Subversion('svn+' + link.url).unpack(location)
        else:
            ## FIXME: handle?
            ## FIXME: magic signatures?
            logger.fatal('Cannot unpack file %s (downloaded from %s, content-type: %s); cannot detect archive format'
                         % (filename, location, content_type))
            raise InstallationError('Cannot determine archive format of %s' % location)

    def unzip_file(self, filename, location, flatten=True):
        """Unzip the file (zip file located at filename) to the destination
        location"""
        if not os.path.exists(location):
            os.makedirs(location)
        zipfp = open(filename, 'rb')
        try:
            zip = zipfile.ZipFile(zipfp)
            leading = has_leading_dir(zip.namelist()) and flatten
            for name in zip.namelist():
                data = zip.read(name)
                fn = name
                if leading:
                    fn = split_leading_dir(name)[1]
                fn = os.path.join(location, fn)
                dir = os.path.dirname(fn)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                if fn.endswith('/') or fn.endswith('\\'):
                    # A directory
                    if not os.path.exists(fn):
                        os.makedirs(fn)
                else:
                    fp = open(fn, 'wb')
                    try:
                        fp.write(data)
                    finally:
                        fp.close()
        finally:
            zipfp.close()

    def untar_file(self, filename, location):
        """Untar the file (tar file located at filename) to the destination location"""
        if not os.path.exists(location):
            os.makedirs(location)
        if filename.lower().endswith('.gz') or filename.lower().endswith('.tgz'):
            mode = 'r:gz'
        elif filename.lower().endswith('.bz2') or filename.lower().endswith('.tbz'):
            mode = 'r:bz2'
        elif filename.lower().endswith('.tar'):
            mode = 'r'
        else:
            logger.warn('Cannot determine compression type for file %s' % filename)
            mode = 'r:*'
        tar = tarfile.open(filename, mode)
        try:
            leading = has_leading_dir([member.name for member in tar.getmembers()])
            for member in tar.getmembers():
                fn = member.name
                if leading:
                    fn = split_leading_dir(fn)[1]
                path = os.path.join(location, fn)
                if member.isdir():
                    if not os.path.exists(path):
                        os.makedirs(path)
                else:
                    try:
                        fp = tar.extractfile(member)
                    except (KeyError, AttributeError), e:
                        # Some corrupt tar files seem to produce this
                        # (specifically bad symlinks)
                        logger.warn(
                            'In the tar file %s the member %s is invalid: %s'
                            % (filename, member.name, e))
                        continue
                    if not os.path.exists(os.path.dirname(path)):
                        os.makedirs(os.path.dirname(path))
                    destfp = open(path, 'wb')
                    try:
                        shutil.copyfileobj(fp, destfp)
                    finally:
                        destfp.close()
                    fp.close()
        finally:
            tar.close()

    def install(self, install_options):
        """Install everything in this set (after having downloaded and unpacked the packages)"""
        to_install = sorted([r for r in self.requirements.values()
                             if self.upgrade or not r.satisfied_by],
                            key=lambda p: p.name.lower())
        if to_install:
            logger.notify('Installing collected packages: %s' % (', '.join([req.name for req in to_install])))
        logger.indent += 2
        try:
            for requirement in to_install:
                if requirement.conflicts_with:
                    logger.notify('Found existing installation: %s'
                                  % requirement.conflicts_with)
                    logger.indent += 2
                    try:
                        requirement.uninstall(auto_confirm=True)
                    finally:
                        logger.indent -= 2
                try:
                    requirement.install(install_options)
                except:
                    # if install did not succeed, rollback previous uninstall
                    if requirement.conflicts_with and not requirement.install_succeeded:
                        requirement.rollback_uninstall()
                    raise
                requirement.remove_temporary_source()
        finally:
            logger.indent -= 2
        self.successfully_installed = to_install

    def create_bundle(self, bundle_filename):
        ## FIXME: can't decide which is better; zip is easier to read
        ## random files from, but tar.bz2 is smaller and not as lame a
        ## format.

        ## FIXME: this file should really include a manifest of the
        ## packages, maybe some other metadata files.  It would make
        ## it easier to detect as well.
        zip = zipfile.ZipFile(bundle_filename, 'w', zipfile.ZIP_DEFLATED)
        vcs_dirs = []
        for dir, basename in (self.build_dir, 'build'), (self.src_dir, 'src'):
            dir = os.path.normcase(os.path.abspath(dir))
            for dirpath, dirnames, filenames in os.walk(dir):
                for backend in vcs.backends:
                    vcs_backend = backend()
                    vcs_url = vcs_rev = None
                    if vcs_backend.dirname in dirnames:
                        for vcs_dir in vcs_dirs:
                            if dirpath.startswith(vcs_dir):
                                # vcs bundle file already in parent directory
                                break
                        else:
                            vcs_url, vcs_rev = vcs_backend.get_info(
                                os.path.join(dir, dirpath))
                            vcs_dirs.append(dirpath)
                        vcs_bundle_file = vcs_backend.bundle_file
                        vcs_guide = vcs_backend.guide % {'url': vcs_url,
                                                         'rev': vcs_rev}
                        dirnames.remove(vcs_backend.dirname)
                        break
                if 'pip-egg-info' in dirnames:
                    dirnames.remove('pip-egg-info')
                for dirname in dirnames:
                    dirname = os.path.join(dirpath, dirname)
                    name = self._clean_zip_name(dirname, dir)
                    zip.writestr(basename + '/' + name + '/', '')
                for filename in filenames:
                    if filename == 'pip-delete-this-directory.txt':
                        continue
                    filename = os.path.join(dirpath, filename)
                    name = self._clean_zip_name(filename, dir)
                    zip.write(filename, basename + '/' + name)
                if vcs_url:
                    name = os.path.join(dirpath, vcs_bundle_file)
                    name = self._clean_zip_name(name, dir)
                    zip.writestr(basename + '/' + name, vcs_guide)

        zip.writestr('pip-manifest.txt', self.bundle_requirements())
        zip.close()
        # Unlike installation, this will always delete the build directories
        logger.info('Removing temporary build dir %s and source dir %s'
                    % (self.build_dir, self.src_dir))
        for dir in self.build_dir, self.src_dir:
            if os.path.exists(dir):
                shutil.rmtree(dir)


    BUNDLE_HEADER = '''\
# This is a pip bundle file, that contains many source packages
# that can be installed as a group.  You can install this like:
#     pip this_file.zip
# The rest of the file contains a list of all the packages included:
'''

    def bundle_requirements(self):
        parts = [self.BUNDLE_HEADER]
        for req in sorted(
            [req for req in self.requirements.values()
             if not req.comes_from],
            key=lambda x: x.name):
            parts.append('%s==%s\n' % (req.name, req.installed_version))
        parts.append('# These packages were installed to satisfy the above requirements:\n')
        for req in sorted(
            [req for req in self.requirements.values()
             if req.comes_from],
            key=lambda x: x.name):
            parts.append('%s==%s\n' % (req.name, req.installed_version))
        ## FIXME: should we do something with self.unnamed_requirements?
        return ''.join(parts)

    def _clean_zip_name(self, name, prefix):
        assert name.startswith(prefix+'/'), (
            "name %r doesn't start with prefix %r" % (name, prefix))
        name = name[len(prefix)+1:]
        name = name.replace(os.path.sep, '/')
        return name

class HTMLPage(object):
    """Represents one page, along with its URL"""

    ## FIXME: these regexes are horrible hacks:
    _homepage_re = re.compile(r'<th>\s*home\s*page', re.I)
    _download_re = re.compile(r'<th>\s*download\s+url', re.I)
    ## These aren't so aweful:
    _rel_re = re.compile("""<[^>]*\srel\s*=\s*['"]?([^'">]+)[^>]*>""", re.I)
    _href_re = re.compile('href=(?:"([^"]*)"|\'([^\']*)\'|([^>\\s\\n]*))', re.I|re.S)
    _base_re = re.compile(r"""<base\s+href\s*=\s*['"]?([^'">]+)""", re.I)

    def __init__(self, content, url, headers=None):
        self.content = content
        self.url = url
        self.headers = headers

    def __str__(self):
        return self.url

    @classmethod
    def get_page(cls, link, req, cache=None, skip_archives=True):
        url = link.url
        url = url.split('#', 1)[0]
        if cache.too_many_failures(url):
            return None
        if url.lower().startswith('svn'):
            logger.debug('Cannot look at svn URL %s' % link)
            return None
        if cache is not None:
            inst = cache.get_page(url)
            if inst is not None:
                return inst
        try:
            if skip_archives:
                if cache is not None:
                    if cache.is_archive(url):
                        return None
                filename = link.filename
                for bad_ext in ['.tar', '.tar.gz', '.tar.bz2', '.tgz', '.zip']:
                    if filename.endswith(bad_ext):
                        content_type = cls._get_content_type(url)
                        if content_type.lower().startswith('text/html'):
                            break
                        else:
                            logger.debug('Skipping page %s because of Content-Type: %s' % (link, content_type))
                            if cache is not None:
                                cache.set_is_archive(url)
                            return None
            logger.debug('Getting page %s' % url)
            resp = urllib2.urlopen(url)
            real_url = resp.geturl()
            headers = resp.info()
            inst = cls(resp.read(), real_url, headers)
        except (urllib2.HTTPError, urllib2.URLError, socket.timeout, socket.error), e:
            desc = str(e)
            if isinstance(e, socket.timeout):
                log_meth = logger.info
                level =1
                desc = 'timed out'
            elif isinstance(e, urllib2.URLError):
                log_meth = logger.info
                if hasattr(e, 'reason') and isinstance(e.reason, socket.timeout):
                    desc = 'timed out'
                    level = 1
                else:
                    level = 2
            elif isinstance(e, urllib2.HTTPError) and e.code == 404:
                ## FIXME: notify?
                log_meth = logger.info
                level = 2
            else:
                log_meth = logger.info
                level = 1
            log_meth('Could not fetch URL %s: %s' % (link, desc))
            log_meth('Will skip URL %s when looking for download links for %s' % (link.url, req))
            if cache is not None:
                cache.add_page_failure(url, level)
            return None
        if cache is not None:
            cache.add_page([url, real_url], inst)
        return inst

    @staticmethod
    def _get_content_type(url):
        """Get the Content-Type of the given url, using a HEAD request"""
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        if scheme == 'http':
            ConnClass = httplib.HTTPConnection
        elif scheme == 'https':
            ConnClass = httplib.HTTPSConnection
        else:
            ## FIXME: some warning or something?
            ## assertion error?
            return ''
        if query:
            path += '?' + query
        conn = ConnClass(netloc)
        try:
            conn.request('HEAD', path, headers={'Host': netloc})
            resp = conn.getresponse()
            if resp.status != 200:
                ## FIXME: doesn't handle redirects
                return ''
            return resp.getheader('Content-Type') or ''
        finally:
            conn.close()

    @property
    def base_url(self):
        if not hasattr(self, "_base_url"):
            match = self._base_re.search(self.content)
            if match:
                self._base_url = match.group(1)
            else:
                self._base_url = self.url
        return self._base_url

    @property
    def links(self):
        """Yields all links in the page"""
        for match in self._href_re.finditer(self.content):
            url = match.group(1) or match.group(2) or match.group(3)
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    def rel_links(self):
        for url in self.explicit_rel_links():
            yield url
        for url in self.scraped_rel_links():
            yield url

    def explicit_rel_links(self, rels=('homepage', 'download')):
        """Yields all links with the given relations"""
        for match in self._rel_re.finditer(self.content):
            found_rels = match.group(1).lower().split()
            for rel in rels:
                if rel in found_rels:
                    break
            else:
                continue
            match = self._href_re.search(match.group(0))
            if not match:
                continue
            url = match.group(1) or match.group(2) or match.group(3)
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    def scraped_rel_links(self):
        for regex in (self._homepage_re, self._download_re):
            match = regex.search(self.content)
            if not match:
                continue
            href_match = self._href_re.search(self.content, pos=match.end())
            if not href_match:
                continue
            url = match.group(1) or match.group(2) or match.group(3)
            if not url:
                continue
            url = self.clean_link(urlparse.urljoin(self.base_url, url))
            yield Link(url, self)

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)

    def clean_link(self, url):
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self._clean_re.sub(
            lambda match: '%%%2x' % ord(match.group(0)), url)

class PageCache(object):
    """Cache of HTML pages"""

    failure_limit = 3

    def __init__(self):
        self._failures = {}
        self._pages = {}
        self._archives = {}

    def too_many_failures(self, url):
        return self._failures.get(url, 0) >= self.failure_limit

    def get_page(self, url):
        return self._pages.get(url)

    def is_archive(self, url):
        return self._archives.get(url, False)

    def set_is_archive(self, url, value=True):
        self._archives[url] = value

    def add_page_failure(self, url, level):
        self._failures[url] = self._failures.get(url, 0)+level

    def add_page(self, urls, page):
        for url in urls:
            self._pages[url] = page

class Link(object):

    def __init__(self, url, comes_from=None):
        self.url = url
        self.comes_from = comes_from

    def __str__(self):
        if self.comes_from:
            return '%s (from %s)' % (self.url, self.comes_from)
        else:
            return self.url

    def __repr__(self):
        return '<Link %s>' % self

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    @property
    def filename(self):
        url = self.url
        url = url.split('#', 1)[0]
        url = url.split('?', 1)[0]
        url = url.rstrip('/')
        name = posixpath.basename(url)
        assert name, (
            'URL %r produced no filename' % url)
        return name

    @property
    def scheme(self):
        return urlparse.urlsplit(self.url)[0]

    @property
    def path(self):
        return urlparse.urlsplit(self.url)[2]

    def splitext(self):
        return splitext(posixpath.basename(self.path.rstrip('/')))

    _egg_fragment_re = re.compile(r'#egg=([^&]*)')

    @property
    def egg_fragment(self):
        match = self._egg_fragment_re.search(self.url)
        if not match:
            return None
        return match.group(1)

    _md5_re = re.compile(r'md5=([a-f0-9]+)')

    @property
    def md5_hash(self):
        match = self._md5_re.search(self.url)
        if match:
            return match.group(1)
        return None

    @property
    def show_url(self):
        return posixpath.basename(self.url.split('#', 1)[0].split('?', 1)[0])

############################################################
## Writing freeze files


class FrozenRequirement(object):

    def __init__(self, name, req, editable, comments=()):
        self.name = name
        self.req = req
        self.editable = editable
        self.comments = comments

    _rev_re = re.compile(r'-r(\d+)$')
    _date_re = re.compile(r'-(20\d\d\d\d\d\d)$')

    @classmethod
    def from_dist(cls, dist, dependency_links, find_tags=False):
        location = os.path.normcase(os.path.abspath(dist.location))
        comments = []
        if vcs.get_backend_name(location):
            editable = True
            req = get_src_requirement(dist, location, find_tags)
            if req is None:
                logger.warn('Could not determine repository location of %s' % location)
                comments.append('## !! Could not determine repository location')
                req = dist.as_requirement()
                editable = False
        else:
            editable = False
            req = dist.as_requirement()
            specs = req.specs
            assert len(specs) == 1 and specs[0][0] == '=='
            version = specs[0][1]
            ver_match = cls._rev_re.search(version)
            date_match = cls._date_re.search(version)
            if ver_match or date_match:
                svn_backend = vcs.get_backend('svn')
                if svn_backend:
                    svn_location = svn_backend(
                        ).get_location(dist, dependency_links)
                if not svn_location:
                    logger.warn(
                        'Warning: cannot find svn location for %s' % req)
                    comments.append('## FIXME: could not find svn URL in dependency_links for this package:')
                else:
                    comments.append('# Installing as editable to satisfy requirement %s:' % req)
                    if ver_match:
                        rev = ver_match.group(1)
                    else:
                        rev = '{%s}' % date_match.group(1)
                    editable = True
                    req = 'svn+%s@%s#egg=%s' % (svn_location, rev, cls.egg_name(dist))
        return cls(dist.project_name, req, editable, comments)

    @staticmethod
    def egg_name(dist):
        name = dist.egg_name()
        match = re.search(r'-py\d\.\d$', name)
        if match:
            name = name[:match.start()]
        return name

    def __str__(self):
        req = self.req
        if self.editable:
            req = '-e %s' % req
        return '\n'.join(list(self.comments)+[str(req)])+'\n'

class VersionControl(object):
    name = ''
    dirname = ''

    def __init__(self, url=None, *args, **kwargs):
        self.url = url
        self._cmd = None
        super(VersionControl, self).__init__(*args, **kwargs)

    def _filter(self, line):
        return (Logger.INFO, line)

    @property
    def cmd(self):
        if self._cmd is not None:
            return self._cmd
        command = find_command(self.name)
        if command is None:
            raise BadCommand('Cannot find command %s' % self.name)
        logger.info('Found command %s at %s' % (self.name, command))
        self._cmd = command
        return command

    def get_url_rev(self):
        """
        Returns the correct repository URL and revision by parsing the given
        repository URL
        """
        url = self.url.split('+', 1)[1]
        scheme, netloc, path, query, frag = urlparse.urlsplit(url)
        rev = None
        if '@' in path:
            path, rev = path.rsplit('@', 1)
        url = urlparse.urlunsplit((scheme, netloc, path, query, ''))
        return url, rev

    def get_info(self, location):
        """
        Returns (url, revision), where both are strings
        """
        assert not location.rstrip('/').endswith(self.dirname), 'Bad directory: %s' % location
        return self.get_url(location), self.get_revision(location)

    def normalize_url(self, url):
        """
        Normalize a URL for comparison by unquoting it and removing any trailing slash.
        """
        return urllib.unquote(url).rstrip('/')

    def compare_urls(self, url1, url2):
        """
        Compare two repo URLs for identity, ignoring incidental differences.
        """
        return (self.normalize_url(url1) == self.normalize_url(url2))

    def parse_vcs_bundle_file(self, content):
        """
        Takes the contents of the bundled text file that explains how to revert
        the stripped off version control data of the given package and returns
        the URL and revision of it.
        """
        raise NotImplementedError

    def obtain(self, dest):
        """
        Called when installing or updating an editable package, takes the
        source path of the checkout.
        """
        raise NotImplementedError

    def switch(self, dest, url, rev_options):
        """
        Switch the repo at ``dest`` to point to ``URL``.
        """
        raise NotImplemented

    def update(self, dest, rev_options):
        """
        Update an already-existing repo to the given ``rev_options``.
        """
        raise NotImplementedError

    def check_destination(self, dest, url, rev_options, rev_display):
        """
        Prepare a location to receive a checkout/clone.

        Return True if the location is ready for (and requires) a
        checkout/clone, False otherwise.
        """
        checkout = True
        prompt = False
        if os.path.exists(dest):
            checkout = False
            if os.path.exists(os.path.join(dest, self.dirname)):
                existing_url = self.get_url(dest)
                if self.compare_urls(existing_url, url):
                    logger.info('%s in %s exists, and has correct URL (%s)'
                                % (self.repo_name.title(), display_path(dest), url))
                    logger.notify('Updating %s %s%s'
                                  % (display_path(dest), self.repo_name, rev_display))
                    self.update(dest, rev_options)
                else:
                    logger.warn('%s %s in %s exists with URL %s'
                                % (self.name, self.repo_name, display_path(dest), existing_url))
                    prompt = ('(s)witch, (i)gnore, (w)ipe, (b)ackup ', ('s', 'i', 'w', 'b'))
            else:
                logger.warn('Directory %s already exists, and is not a %s %s.'
                            % (dest, self.name, self.repo_name))
                prompt = ('(i)gnore, (w)ipe, (b)ackup ', ('i', 'w', 'b'))
        if prompt:
            logger.warn('The plan is to install the %s repository %s'
                        % (self.name, url))
            response = ask('What to do?  %s' % prompt[0], prompt[1])

            if response == 's':
                logger.notify('Switching %s %s to %s%s'
                              % (self.repo_name, display_path(dest), url, rev_display))
                self.switch(dest, url, rev_options)
            elif response == 'i':
                # do nothing
                pass
            elif response == 'w':
                logger.warn('Deleting %s' % display_path(dest))
                shutil.rmtree(dest)
                checkout = True
            elif response == 'b':
                dest_dir = backup_dir(dest)
                logger.warn('Backing up %s to %s'
                            % (display_path(dest), dest_dir))
                shutil.move(dest, dest_dir)
                checkout = True
        return checkout

    def unpack(self, location):
        raise NotImplementedError

    def get_src_requirement(self, dist, location, find_tags=False):
        raise NotImplementedError

_svn_xml_url_re = re.compile('url="([^"]+)"')
_svn_rev_re = re.compile('committed-rev="(\d+)"')
_svn_url_re = re.compile(r'URL: (.+)')
_svn_revision_re = re.compile(r'Revision: (.+)')

class Subversion(VersionControl):
    name = 'svn'
    dirname = '.svn'
    repo_name = 'checkout'
    schemes = ('svn', 'svn+ssh', 'svn+http', 'svn+https')
    bundle_file = 'svn-checkout.txt'
    guide = ('# This was an svn checkout; to make it a checkout again run:\n'
            'svn checkout --force -r %(rev)s %(url)s .\n')

    def get_info(self, location):
        """Returns (url, revision), where both are strings"""
        assert not location.rstrip('/').endswith(self.dirname), 'Bad directory: %s' % location
        output = call_subprocess(
            ['svn', 'info', location], show_stdout=False, extra_environ={'LANG': 'C'})
        match = _svn_url_re.search(output)
        if not match:
            logger.warn('Cannot determine URL of svn checkout %s' % display_path(location))
            logger.info('Output that cannot be parsed: \n%s' % output)
            return None, None
        url = match.group(1).strip()
        match = _svn_revision_re.search(output)
        if not match:
            logger.warn('Cannot determine revision of svn checkout %s' % display_path(location))
            logger.info('Output that cannot be parsed: \n%s' % output)
            return url, None
        return url, match.group(1)

    def get_url(self, location):
        return self.get_info(location)[0]

    def get_revision(self, location):
        return self.get_info(location)[1]

    def parse_vcs_bundle_file(self, content):
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue
            match = re.search(r'^-r\s*([^ ])?', line)
            if not match:
                return None, None
            rev = match.group(1)
            rest = line[match.end():].strip().split(None, 1)[0]
            return rest, rev
        return None, None

    def unpack(self, location):
        """Check out the svn repository at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Checking out svn repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                # Subversion doesn't like to check out over an existing directory
                # --force fixes this, but was only added in svn 1.5
                shutil.rmtree(location, onerror=rmtree_errorhandler)
            call_subprocess(
                ['svn', 'checkout', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def export(self, location):
        """Export the svn repository at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Checking out svn repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                # Subversion doesn't like to check out over an existing directory
                # --force fixes this, but was only added in svn 1.5
                shutil.rmtree(location, onerror=rmtree_errorhandler)
            call_subprocess(
                ['svn', 'export', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def switch(self, dest, url, rev_options):
        call_subprocess(
            ['svn', 'switch'] + rev_options + [url, dest])

    def update(self, dest, rev_options):
        call_subprocess(
            ['svn', 'update'] + rev_options + [dest])

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        if rev:
            rev_options = ['-r', rev]
            rev_display = ' (to revision %s)' % rev
        else:
            rev_options = []
            rev_display = ''
        if self.check_destination(dest, url, rev_options, rev_display):
            logger.notify('Checking out %s%s to %s'
                          % (url, rev_display, display_path(dest)))
            call_subprocess(
                ['svn', 'checkout', '-q'] + rev_options + [url, dest])

    def get_location(self, dist, dependency_links):
        egg_fragment_re = re.compile(r'#egg=(.*)$')
        for url in dependency_links:
            egg_fragment = Link(url).egg_fragment
            if not egg_fragment:
                continue
            if '-' in egg_fragment:
                ## FIXME: will this work when a package has - in the name?
                key = '-'.join(egg_fragment.split('-')[:-1]).lower()
            else:
                key = egg_fragment
            if key == dist.key:
                return url.split('#', 1)[0]
        return None

    def get_revision(self, location):
        """
        Return the maximum revision for all files under a given location
        """
        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, files in os.walk(location):
            if self.dirname not in dirs:
                dirs[:] = []
                continue    # no sense walking uncontrolled subdirs
            dirs.remove(self.dirname)
            entries_fn = os.path.join(base, self.dirname, 'entries')
            if not os.path.exists(entries_fn):
                ## FIXME: should we warn?
                continue
            f = open(entries_fn)
            data = f.read()
            f.close()

            if data.startswith('8') or data.startswith('9') or data.startswith('10'):
                data = map(str.splitlines,data.split('\n\x0c\n'))
                del data[0][0]  # get rid of the '8'
                dirurl = data[0][3]
                revs = [int(d[9]) for d in data if len(d)>9 and d[9]]+[0]
                if revs:
                    localrev = max(revs)
                else:
                    localrev = 0
            elif data.startswith('<?xml'):
                dirurl = _svn_xml_url_re.search(data).group(1)    # get repository URL
                revs = [int(m.group(1)) for m in _svn_rev_re.finditer(data)]+[0]
                if revs:
                    localrev = max(revs)
                else:
                    localrev = 0
            else:
                logger.warn("Unrecognized .svn/entries format; skipping %s", base)
                dirs[:] = []
                continue
            if base == location:
                base_url = dirurl+'/'   # save the root url
            elif not dirurl.startswith(base_url):
                dirs[:] = []
                continue    # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return revision

    def get_url(self, location):
        # In cases where the source is in a subdirectory, not alongside setup.py
        # we have to look up in the location until we find a real setup.py
        orig_location = location
        while not os.path.exists(os.path.join(location, 'setup.py')):
            last_location = location
            location = os.path.dirname(location)
            if location == last_location:
                # We've traversed up to the root of the filesystem without finding setup.py
                logger.warn("Could not find setup.py for directory %s (tried all parent directories)"
                            % orig_location)
                return None
        f = open(os.path.join(location, self.dirname, 'entries'))
        data = f.read()
        f.close()
        if data.startswith('8') or data.startswith('9') or data.startswith('10'):
            data = map(str.splitlines,data.split('\n\x0c\n'))
            del data[0][0]  # get rid of the '8'
            return data[0][3]
        elif data.startswith('<?xml'):
            match = _svn_xml_url_re.search(data)
            if not match:
                raise ValueError('Badly formatted data: %r' % data)
            return match.group(1)    # get repository URL
        else:
            logger.warn("Unrecognized .svn/entries format in %s" % location)
            # Or raise exception?
            return None

    def get_tag_revs(self, svn_tag_url):
        stdout = call_subprocess(
            ['svn', 'ls', '-v', svn_tag_url], show_stdout=False)
        results = []
        for line in stdout.splitlines():
            parts = line.split()
            rev = int(parts[0])
            tag = parts[-1].strip('/')
            results.append((tag, rev))
        return results

    def find_tag_match(self, rev, tag_revs):
        best_match_rev = None
        best_tag = None
        for tag, tag_rev in tag_revs:
            if (tag_rev > rev and
                (best_match_rev is None or best_match_rev > tag_rev)):
                # FIXME: Is best_match > tag_rev really possible?
                # or is it a sign something is wacky?
                best_match_rev = tag_rev
                best_tag = tag
        return best_tag

    def get_src_requirement(self, dist, location, find_tags=False):
        repo = self.get_url(location)
        if repo is None:
            return None
        parts = repo.split('/')
        ## FIXME: why not project name?
        egg_project_name = dist.egg_name().split('-', 1)[0]
        rev = self.get_revision(location)
        if parts[-2] in ('tags', 'tag'):
            # It's a tag, perfect!
            full_egg_name = '%s-%s' % (egg_project_name, parts[-1])
        elif parts[-2] in ('branches', 'branch'):
            # It's a branch :(
            full_egg_name = '%s-%s-r%s' % (dist.egg_name(), parts[-1], rev)
        elif parts[-1] == 'trunk':
            # Trunk :-/
            full_egg_name = '%s-dev_r%s' % (dist.egg_name(), rev)
            if find_tags:
                tag_url = '/'.join(parts[:-1]) + '/tags'
                tag_revs = self.get_tag_revs(tag_url)
                match = self.find_tag_match(rev, tag_revs)
                if match:
                    logger.notify('trunk checkout %s seems to be equivalent to tag %s' % match)
                    repo = '%s/%s' % (tag_url, match)
                    full_egg_name = '%s-%s' % (egg_project_name, match)
        else:
            # Don't know what it is
            logger.warn('svn URL does not fit normal structure (tags/branches/trunk): %s' % repo)
            full_egg_name = '%s-dev_r%s' % (egg_project_name, rev)
        return 'svn+%s@%s#egg=%s' % (repo, rev, full_egg_name)

vcs.register(Subversion)


class Git(VersionControl):
    name = 'git'
    dirname = '.git'
    repo_name = 'clone'
    schemes = ('git', 'git+http', 'git+ssh', 'git+git')
    bundle_file = 'git-clone.txt'
    guide = ('# This was a Git repo; to make it a repo again run:\n'
        'git init\ngit remote add origin %(url)s -f\ngit checkout %(rev)s\n')

    def parse_vcs_bundle_file(self, content):
        url = rev = None
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue
            url_match = re.search(r'git\s*remote\s*add\s*origin(.*)\s*-f', line)
            if url_match:
                url = url_match.group(1).strip()
            rev_match = re.search(r'^git\s*checkout\s*-q\s*(.*)\s*', line)
            if rev_match:
                rev = rev_match.group(1).strip()
            if url and rev:
                return url, rev
        return None, None

    def unpack(self, location):
        """Clone the Git repository at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Cloning Git repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                os.rmdir(location)
            call_subprocess(
                [self.cmd, 'clone', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def export(self, location):
        """Export the Git repository at the url to the destination location"""
        temp_dir = tempfile.mkdtemp('-export', 'pip-')
        self.unpack(temp_dir)
        try:
            if not location.endswith('/'):
                location = location + '/'
            call_subprocess(
                [self.cmd, 'checkout-index', '-a', '-f', '--prefix', location],
                filter_stdout=self._filter, show_stdout=False, cwd=temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    def check_rev_options(self, rev, dest, rev_options):
        """Check the revision options before checkout to compensate that tags
        and branches may need origin/ as a prefix"""
        if rev is None:
            # bail and use preset
            return rev_options
        revisions = self.get_tag_revs(dest)
        revisions.update(self.get_branch_revs(dest))
        if rev in revisions:
            # if rev is a sha
            return [rev]
        inverse_revisions = dict((v,k) for k, v in revisions.iteritems())
        if rev not in inverse_revisions: # is rev a name or tag?
            origin_rev = 'origin/%s' % rev
            if origin_rev in inverse_revisions:
                rev = inverse_revisions[origin_rev]
            else:
                logger.warn("Could not find a tag or branch '%s', assuming commit." % rev)
        return [rev]

    def switch(self, dest, url, rev_options):

        call_subprocess(
            [self.cmd, 'config', 'remote.origin.url', url], cwd=dest)
        call_subprocess(
            [self.cmd, 'checkout', '-q'] + rev_options, cwd=dest)

    def update(self, dest, rev_options):
        call_subprocess([self.cmd, 'fetch', '-q'], cwd=dest)
        call_subprocess(
            [self.cmd, 'checkout', '-q', '-f'] + rev_options, cwd=dest)

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        if rev:
            rev_options = [rev]
            rev_display = ' (to %s)' % rev
        else:
            rev_options = ['origin/master']
            rev_display = ''
        if self.check_destination(dest, url, rev_options, rev_display):
            logger.notify('Cloning %s%s to %s' % (url, rev_display, display_path(dest)))
            call_subprocess(
                [self.cmd, 'clone', '-q', url, dest])
            rev_options = self.check_rev_options(rev, dest, rev_options)
            call_subprocess(
                [self.cmd, 'checkout', '-q'] + rev_options, cwd=dest)

    def get_url(self, location):
        url = call_subprocess(
            [self.cmd, 'config', 'remote.origin.url'],
            show_stdout=False, cwd=location)
        return url.strip()

    def get_revision(self, location):
        current_rev = call_subprocess(
            [self.cmd, 'rev-parse', 'HEAD'], show_stdout=False, cwd=location)
        return current_rev.strip()

    def get_tag_revs(self, location):
        tags = call_subprocess(
            [self.cmd, 'tag'], show_stdout=False, cwd=location)
        tag_revs = []
        for line in tags.splitlines():
            tag = line.strip()
            rev = call_subprocess(
                [self.cmd, 'rev-parse', tag], show_stdout=False, cwd=location)
            tag_revs.append((rev.strip(), tag))
        tag_revs = dict(tag_revs)
        return tag_revs

    def get_branch_revs(self, location):
        branches = call_subprocess(
            [self.cmd, 'branch', '-r'], show_stdout=False, cwd=location)
        branch_revs = []
        for line in branches.splitlines():
            line = line.split('->')[0].strip()
            branch = "".join([b for b in line.split() if b != '*'])
            rev = call_subprocess(
                [self.cmd, 'rev-parse', branch], show_stdout=False, cwd=location)
            branch_revs.append((rev.strip(), branch))
        branch_revs = dict(branch_revs)
        return branch_revs

    def get_src_requirement(self, dist, location, find_tags):
        repo = self.get_url(location)
        if not repo.lower().startswith('git:'):
            repo = 'git+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        if not repo:
            return None
        current_rev = self.get_revision(location)
        tag_revs = self.get_tag_revs(location)
        branch_revs = self.get_branch_revs(location)

        if current_rev in tag_revs:
            # It's a tag
            full_egg_name = '%s-%s' % (egg_project_name, tag_revs[current_rev])
        elif (current_rev in branch_revs and
              branch_revs[current_rev] != 'origin/master'):
            # It's the head of a branch
            full_egg_name = '%s-%s' % (dist.egg_name(),
                                       branch_revs[current_rev].replace('origin/', ''))
        else:
            full_egg_name = '%s-dev' % dist.egg_name()

        return '%s@%s#egg=%s' % (repo, current_rev, full_egg_name)

    def get_url_rev(self):
        """
        Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
        That's required because although they use SSH they sometimes doesn't
        work with a ssh:// scheme (e.g. Github). But we need a scheme for
        parsing. Hence we remove it again afterwards and return it as a stub.
        """
        if not '://' in self.url:
            self.url = self.url.replace('git+', 'git+ssh://')
            url, rev = super(Git, self).get_url_rev()
            url = url.replace('ssh://', '')
            return url, rev
        return super(Git, self).get_url_rev()

vcs.register(Git)

class Mercurial(VersionControl):
    name = 'hg'
    dirname = '.hg'
    repo_name = 'clone'
    schemes = ('hg', 'hg+http', 'hg+https', 'hg+ssh', 'hg+static-http')
    bundle_file = 'hg-clone.txt'
    guide = ('# This was a Mercurial repo; to make it a repo again run:\n'
            'hg init\nhg pull %(url)s\nhg update -r %(rev)s\n')

    def parse_vcs_bundle_file(self, content):
        url = rev = None
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue
            url_match = re.search(r'hg\s*pull\s*(.*)\s*', line)
            if url_match:
                url = url_match.group(1).strip()
            rev_match = re.search(r'^hg\s*update\s*-r\s*(.*)\s*', line)
            if rev_match:
                rev = rev_match.group(1).strip()
            if url and rev:
                return url, rev
        return None, None

    def unpack(self, location):
        """Clone the Hg repository at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Cloning Mercurial repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                os.rmdir(location)
            call_subprocess(
                ['hg', 'clone', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def export(self, location):
        """Export the Hg repository at the url to the destination location"""
        temp_dir = tempfile.mkdtemp('-export', 'pip-')
        self.unpack(temp_dir)
        try:
            call_subprocess(
                ['hg', 'archive', location],
                filter_stdout=self._filter, show_stdout=False, cwd=temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    def switch(self, dest, url, rev_options):
        repo_config = os.path.join(dest, self.dirname, 'hgrc')
        config = ConfigParser.SafeConfigParser()
        try:
            config.read(repo_config)
            config.set('paths', 'default', url)
            config_file = open(repo_config, 'w')
            config.write(config_file)
            config_file.close()
        except (OSError, ConfigParser.NoSectionError), e:
            logger.warn(
                'Could not switch Mercurial repository to %s: %s'
                % (url, e))
        else:
            call_subprocess(['hg', 'update', '-q'] + rev_options, cwd=dest)

    def update(self, dest, rev_options):
        call_subprocess(['hg', 'pull', '-q'], cwd=dest)
        call_subprocess(
            ['hg', 'update', '-q'] + rev_options, cwd=dest)

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        if rev:
            rev_options = [rev]
            rev_display = ' (to revision %s)' % rev
        else:
            rev_options = []
            rev_display = ''
        if self.check_destination(dest, url, rev_options, rev_display):
            logger.notify('Cloning hg %s%s to %s'
                          % (url, rev_display, display_path(dest)))
            call_subprocess(['hg', 'clone', '-q', url, dest])
            call_subprocess(['hg', 'update', '-q'] + rev_options, cwd=dest)

    def get_url(self, location):
        url = call_subprocess(
            ['hg', 'showconfig', 'paths.default'],
            show_stdout=False, cwd=location).strip()
        if url.startswith('/') or url.startswith('\\'):
            url = filename_to_url(url)
        return url.strip()

    def get_tag_revs(self, location):
        tags = call_subprocess(
            ['hg', 'tags'], show_stdout=False, cwd=location)
        tag_revs = []
        for line in tags.splitlines():
            tags_match = re.search(r'([\w\d\.-]+)\s*([\d]+):.*$', line)
            if tags_match:
                tag = tags_match.group(1)
                rev = tags_match.group(2)
                tag_revs.append((rev.strip(), tag.strip()))
        return dict(tag_revs)

    def get_branch_revs(self, location):
        branches = call_subprocess(
            ['hg', 'branches'], show_stdout=False, cwd=location)
        branch_revs = []
        for line in branches.splitlines():
            branches_match = re.search(r'([\w\d\.-]+)\s*([\d]+):.*$', line)
            if branches_match:
                branch = branches_match.group(1)
                rev = branches_match.group(2)
                branch_revs.append((rev.strip(), branch.strip()))
        return dict(branch_revs)

    def get_revision(self, location):
        current_revision = call_subprocess(
            ['hg', 'parents', '--template={rev}'],
            show_stdout=False, cwd=location).strip()
        return current_revision

    def get_revision_hash(self, location):
        current_rev_hash = call_subprocess(
            ['hg', 'parents', '--template={node}'],
            show_stdout=False, cwd=location).strip()
        return current_rev_hash

    def get_src_requirement(self, dist, location, find_tags):
        repo = self.get_url(location)
        if not repo.lower().startswith('hg:'):
            repo = 'hg+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        if not repo:
            return None
        current_rev = self.get_revision(location)
        current_rev_hash = self.get_revision_hash(location)
        tag_revs = self.get_tag_revs(location)
        branch_revs = self.get_branch_revs(location)
        if current_rev in tag_revs:
            # It's a tag
            full_egg_name = '%s-%s' % (egg_project_name, tag_revs[current_rev])
        elif current_rev in branch_revs:
            # It's the tip of a branch
            full_egg_name = '%s-%s' % (dist.egg_name(), branch_revs[current_rev])
        else:
            full_egg_name = '%s-dev' % dist.egg_name()
        return '%s@%s#egg=%s' % (repo, current_rev_hash, full_egg_name)

vcs.register(Mercurial)


class Bazaar(VersionControl):
    name = 'bzr'
    dirname = '.bzr'
    repo_name = 'branch'
    bundle_file = 'bzr-branch.txt'
    schemes = ('bzr', 'bzr+http', 'bzr+https', 'bzr+ssh', 'bzr+sftp', 'bzr+ftp')
    guide = ('# This was a Bazaar branch; to make it a branch again run:\n'
             'bzr branch -r %(rev)s %(url)s .\n')

    def parse_vcs_bundle_file(self, content):
        url = rev = None
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue
            match = re.search(r'^bzr\s*branch\s*-r\s*(\d*)', line)
            if match:
                rev = match.group(1).strip()
            url = line[match.end():].strip().split(None, 1)[0]
            if url and rev:
                return url, rev
        return None, None

    def unpack(self, location):
        """Get the bzr branch at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Checking out bzr repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                os.rmdir(location)
            call_subprocess(
                [self.cmd, 'branch', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def export(self, location):
        """Export the Bazaar repository at the url to the destination location"""
        temp_dir = tempfile.mkdtemp('-export', 'pip-')
        self.unpack(temp_dir)
        if os.path.exists(location):
            # Remove the location to make sure Bazaar can export it correctly
            shutil.rmtree(location, onerror=rmtree_errorhandler)
        try:
            call_subprocess([self.cmd, 'export', location], cwd=temp_dir,
                            filter_stdout=self._filter, show_stdout=False)
        finally:
            shutil.rmtree(temp_dir)

    def switch(self, dest, url, rev_options):
        call_subprocess([self.cmd, 'switch', url], cwd=dest)

    def update(self, dest, rev_options):
        call_subprocess(
            [self.cmd, 'pull', '-q'] + rev_options, cwd=dest)

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        if rev:
            rev_options = ['-r', rev]
            rev_display = ' (to revision %s)' % rev
        else:
            rev_options = []
            rev_display = ''
        if self.check_destination(dest, url, rev_options, rev_display):
            logger.notify('Checking out %s%s to %s'
                          % (url, rev_display, display_path(dest)))
            call_subprocess(
                [self.cmd, 'branch', '-q'] + rev_options + [url, dest])

    def get_url_rev(self):
        # hotfix the URL scheme after removing bzr+ from bzr+ssh:// readd it
        url, rev = super(Bazaar, self).get_url_rev()
        if url.startswith('ssh://'):
            url = 'bzr+' + url
        return url, rev

    def get_url(self, location):
        urls = call_subprocess(
            [self.cmd, 'info'], show_stdout=False, cwd=location)
        for line in urls.splitlines():
            line = line.strip()
            for x in ('checkout of branch: ',
                      'parent branch: '):
                if line.startswith(x):
                    return line.split(x)[1]
        return None

    def get_revision(self, location):
        revision = call_subprocess(
            [self.cmd, 'revno'], show_stdout=False, cwd=location)
        return revision.splitlines()[-1]

    def get_tag_revs(self, location):
        tags = call_subprocess(
            [self.cmd, 'tags'], show_stdout=False, cwd=location)
        tag_revs = []
        for line in tags.splitlines():
            tags_match = re.search(r'([.\w-]+)\s*(.*)$', line)
            if tags_match:
                tag = tags_match.group(1)
                rev = tags_match.group(2)
                tag_revs.append((rev.strip(), tag.strip()))
        return dict(tag_revs)

    def get_src_requirement(self, dist, location, find_tags):
        repo = self.get_url(location)
        if not repo.lower().startswith('bzr:'):
            repo = 'bzr+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        if not repo:
            return None
        current_rev = self.get_revision(location)
        tag_revs = self.get_tag_revs(location)

        if current_rev in tag_revs:
            # It's a tag
            tag = tag_revs.get(current_rev, current_rev)
            full_egg_name = '%s-%s' % (egg_project_name, tag_revs[current_rev])
        else:
            full_egg_name = '%s-dev_r%s' % (dist.egg_name(), current_rev)
        return '%s@%s#egg=%s' % (repo, current_rev, full_egg_name)

vcs.register(Bazaar)

def get_src_requirement(dist, location, find_tags):
    version_control = vcs.get_backend_from_location(location)
    if version_control:
        return version_control().get_src_requirement(dist, location, find_tags)
    logger.warn('cannot determine version of editable source in %s (is not SVN checkout, Git clone, Mercurial clone or Bazaar branch)' % location)
    return dist.as_requirement()

############################################################
## Requirement files

_scheme_re = re.compile(r'^(http|https|file):', re.I)
_url_slash_drive_re = re.compile(r'/*([a-z])\|', re.I)
def get_file_content(url, comes_from=None):
    """Gets the content of a file; it may be a filename, file: URL, or
    http: URL.  Returns (location, content)"""
    match = _scheme_re.search(url)
    if match:
        scheme = match.group(1).lower()
        if (scheme == 'file' and comes_from
            and comes_from.startswith('http')):
            raise InstallationError(
                'Requirements file %s references URL %s, which is local'
                % (comes_from, url))
        if scheme == 'file':
            path = url.split(':', 1)[1]
            path = path.replace('\\', '/')
            match = _url_slash_drive_re.match(path)
            if match:
                path = match.group(1) + ':' + path.split('|', 1)[1]
            path = urllib.unquote(path)
            if path.startswith('/'):
                path = '/' + path.lstrip('/')
            url = path
        else:
            ## FIXME: catch some errors
            resp = urllib2.urlopen(url)
            return resp.geturl(), resp.read()
    f = open(url)
    content = f.read()
    f.close()
    return url, content

def parse_requirements(filename, finder=None, comes_from=None, options=None):
    skip_match = None
    skip_regex = options.skip_requirements_regex
    if skip_regex:
        skip_match = re.compile(skip_regex)
    filename, content = get_file_content(filename, comes_from=comes_from)
    for line_number, line in enumerate(content.splitlines()):
        line_number += 1
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if skip_match and skip_match.search(line):
            continue
        if line.startswith('-r') or line.startswith('--requirement'):
            if line.startswith('-r'):
                req_url = line[2:].strip()
            else:
                req_url = line[len('--requirement'):].strip().strip('=')
            if _scheme_re.search(filename):
                # Relative to a URL
                req_url = urlparse.urljoin(filename, url)
            elif not _scheme_re.search(req_url):
                req_url = os.path.join(os.path.dirname(filename), req_url)
            for item in parse_requirements(req_url, finder, comes_from=filename, options=options):
                yield item
        elif line.startswith('-Z') or line.startswith('--always-unzip'):
            # No longer used, but previously these were used in
            # requirement files, so we'll ignore.
            pass
        elif finder and line.startswith('-f') or line.startswith('--find-links'):
            if line.startswith('-f'):
                line = line[2:].strip()
            else:
                line = line[len('--find-links'):].strip().lstrip('=')
            ## FIXME: it would be nice to keep track of the source of
            ## the find_links:
            finder.find_links.append(line)
        elif line.startswith('-i') or line.startswith('--index-url'):
            if line.startswith('-i'):
                line = line[2:].strip()
            else:
                line = line[len('--index-url'):].strip().lstrip('=')
            finder.index_urls = [line]
        elif line.startswith('--extra-index-url'):
            line = line[len('--extra-index-url'):].strip().lstrip('=')
            finder.index_urls.append(line)
        else:
            comes_from = '-r %s (line %s)' % (filename, line_number)
            if line.startswith('-e') or line.startswith('--editable'):
                if line.startswith('-e'):
                    line = line[2:].strip()
                else:
                    line = line[len('--editable'):].strip()
                req = InstallRequirement.from_editable(
                    line, comes_from=comes_from, default_vcs=options.default_vcs)
            else:
                req = InstallRequirement.from_line(line, comes_from)
            yield req

############################################################
## Logging



class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    VERBOSE_DEBUG = logging.DEBUG-1
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [VERBOSE_DEBUG, DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.explicit_levels = False
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                    if self.explicit_levels:
                        ## FIXME: should this be a name, not a level number?
                        rendered = '%02i %s' % (level, rendered)
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(' '*self.indent + msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg
        self.last_message = None

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                # These erase any messages shown with show_progress (besides .'s)
                logger.show_progress('')
                logger.show_progress('')
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self, message=None):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            if message is None:
                sys.stdout.write('.')
                sys.stdout.flush()
            else:
                if self.last_message:
                    padding = ' ' * max(0, len(self.last_message)-len(message))
                else:
                    padding = ''
                sys.stdout.write('\r%s%s%s%s' % (' '*self.indent, self.in_progress, message, padding))
                sys.stdout.flush()
                self.last_message = message

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger()
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None or stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    @classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    def move_stdout_to_stderr(self):
        to_remove = []
        to_add = []
        for consumer_level, consumer in self.consumers:
            if consumer == sys.stdout:
                to_remove.append((consumer_level, consumer))
                to_add.append((consumer_level, sys.stderr))
        for item in to_remove:
            self.consumers.remove(item)
        self.consumers.extend(to_add)


def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True,
                    command_level=Logger.DEBUG, command_desc=None,
                    extra_environ=None):
    if command_desc is None:
        cmd_parts = []
        for part in cmd:
            if ' ' in part or '\n' in part or '"' in part or "'" in part:
                part = '"%s"' % part.replace('"', '\\"')
            cmd_parts.append(part)
        command_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.log(command_level, "Running command %s" % command_desc)
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception, e:
        logger.fatal(
            "Error %s while executing command %s" % (e, command_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        while 1:
            line = stdout.readline()
            if not line:
                break
            line = line.rstrip()
            all_output.append(line + '\n')
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        returned_stdout, returned_stderr = proc.communicate()
        all_output = [returned_stdout or '']
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % command_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise InstallationError(
                "Command %s failed with error code %s"
                % (command_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (command_desc, proc.returncode))
    if stdout is not None:
        return ''.join(all_output)

############################################################
## Utility functions

def is_svn_page(html):
    """Returns true if the page appears to be the index page of an svn repository"""
    return (re.search(r'<title>[^<]*Revision \d+:', html)
            and re.search(r'Powered by (?:<a[^>]*?>)?Subversion', html, re.I))

def file_contents(filename):
    fp = open(filename, 'rb')
    try:
        return fp.read()
    finally:
        fp.close()

def split_leading_dir(path):
    path = str(path)
    path = path.lstrip('/').lstrip('\\')
    if '/' in path and (('\\' in path and path.find('/') < path.find('\\'))
                        or '\\' not in path):
        return path.split('/', 1)
    elif '\\' in path:
        return path.split('\\', 1)
    else:
        return path, ''

def has_leading_dir(paths):
    """Returns true if all the paths have the same leading path name
    (i.e., everything is in one subdirectory in an archive)"""
    common_prefix = None
    for path in paths:
        prefix, rest = split_leading_dir(path)
        if not prefix:
            return False
        elif common_prefix is None:
            common_prefix = prefix
        elif prefix != common_prefix:
            return False
    return True

def format_size(bytes):
    if bytes > 1000*1000:
        return '%.1fMb' % (bytes/1000.0/1000)
    elif bytes > 10*1000:
        return '%iKb' % (bytes/1000)
    elif bytes > 1000:
        return '%.1fKb' % (bytes/1000.0)
    else:
        return '%ibytes' % bytes

_normalize_re = re.compile(r'[^a-z]', re.I)

def normalize_name(name):
    return _normalize_re.sub('-', name.lower())

def make_path_relative(path, rel_to):
    """
    Make a filename relative, where the filename path, and it is
    relative to rel_to

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../../../something/a-file.pth'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../usr/share/something/a-file.pth'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        'a-file.pth'
    """
    path_filename = os.path.basename(path)
    path = os.path.dirname(path)
    path = os.path.normpath(os.path.abspath(path))
    rel_to = os.path.normpath(os.path.abspath(rel_to))
    path_parts = path.strip(os.path.sep).split(os.path.sep)
    rel_to_parts = rel_to.strip(os.path.sep).split(os.path.sep)
    while path_parts and rel_to_parts and path_parts[0] == rel_to_parts[0]:
        path_parts.pop(0)
        rel_to_parts.pop(0)
    full_parts = ['..']*len(rel_to_parts) + path_parts + [path_filename]
    if full_parts == ['']:
        return '.' + os.path.sep
    return os.path.sep.join(full_parts)

def display_path(path):
    """Gives the display value for a given path, making it relative to cwd
    if possible."""
    path = os.path.normcase(os.path.abspath(path))
    if path.startswith(os.getcwd() + os.path.sep):
        path = '.' + path[len(os.getcwd()):]
    return path

def parse_editable(editable_req, default_vcs=None):
    """Parses svn+http://blahblah@rev#egg=Foobar into a requirement
    (Foobar) and a URL"""
    url = editable_req
    if os.path.isdir(url) and os.path.exists(os.path.join(url, 'setup.py')):
        # Treating it as code that has already been checked out
        url = filename_to_url(url)
    if url.lower().startswith('file:'):
        return None, url
    for version_control in vcs:
        if url.lower().startswith('%s:' % version_control):
            url = '%s+%s' % (version_control, url)
    if '+' not in url:
        if default_vcs:
            url = default_vcs + '+' + url
        else:
            raise InstallationError(
                '--editable=%s should be formatted with svn+URL, git+URL, hg+URL or bzr+URL' % editable_req)
    vc_type = url.split('+', 1)[0].lower()
    if not vcs.get_backend(vc_type):
        raise InstallationError(
            'For --editable=%s only svn (svn+URL), Git (git+URL), Mercurial (hg+URL) and Bazaar (bzr+URL) is currently supported' % editable_req)
    match = re.search(r'(?:#|#.*?&)egg=([^&]*)', editable_req)
    if (not match or not match.group(1)) and vcs.get_backend(vc_type):
        parts = [p for p in editable_req.split('#', 1)[0].split('/') if p]
        if parts[-2] in ('tags', 'branches', 'tag', 'branch'):
            req = parts[-3]
        elif parts[-1] == 'trunk':
            req = parts[-2]
        else:
            raise InstallationError(
                '--editable=%s is not the right format; it must have #egg=Package'
                % editable_req)
    else:
        req = match.group(1)
    ## FIXME: use package_to_requirement?
    match = re.search(r'^(.*?)(?:-dev|-\d.*)', req)
    if match:
        # Strip off -dev, -0.2, etc.
        req = match.group(1)
    return req, url

def backup_dir(dir, ext='.bak'):
    """Figure out the name of a directory to back up the given dir to
    (adding .bak, .bak2, etc)"""
    n = 1
    extension = ext
    while os.path.exists(dir + extension):
        n += 1
        extension = ext + str(n)
    return dir + extension

def ask(message, options):
    """Ask the message interactively, with the given possible responses"""
    while 1:
        if os.environ.get('PIP_NO_INPUT'):
            raise Exception('No input was expected ($PIP_NO_INPUT set); question: %s' % message)
        response = raw_input(message)
        response = response.strip().lower()
        if response not in options:
            print 'Your response (%r) was not one of the expected responses: %s' % (
                response, ', '.join(options))
        else:
            return response

def open_logfile_append(filename):
    """Open the named log file in append mode.

    If the file already exists, a separator will also be printed to
    the file to separate past activity from current activity.
    """
    exists = os.path.exists(filename)
    log_fp = open(filename, 'a')
    if exists:
        print >> log_fp, '-'*60
        print >> log_fp, '%s run on %s' % (sys.argv[0], time.strftime('%c'))
    return log_fp

def is_url(name):
    """Returns true if the name looks like a URL"""
    if ':' not in name:
        return False
    scheme = name.split(':', 1)[0].lower()
    return scheme in ['http', 'https', 'file', 'ftp'] + vcs.all_schemes

def is_filename(name):
    if (splitext(name)[1].lower() in ('.zip', '.tar.gz', '.tar.bz2', '.tgz', '.tar', '.pybundle')
        and os.path.exists(name)):
        return True
    if os.path.sep not in name and '/' not in name:
        # Doesn't have any path components, probably a requirement like 'Foo'
        return False
    return True

_drive_re = re.compile('^([a-z]):', re.I)
_url_drive_re = re.compile('^([a-z])[:|]', re.I)

def filename_to_url(filename):
    """
    Convert a path to a file: URL.  The path will be made absolute.
    """
    filename = os.path.normcase(os.path.abspath(filename))
    if _drive_re.match(filename):
        filename = filename[0] + '|' + filename[2:]
    url = urllib.quote(filename)
    url = url.replace(os.path.sep, '/')
    url = url.lstrip('/')
    return 'file:///' + url

def filename_to_url2(filename):
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    filename = os.path.normcase(os.path.abspath(filename))
    drive, filename = os.path.splitdrive(filename)
    filepath = filename.split(os.path.sep)
    url = '/'.join([urllib.quote(part) for part in filepath])
    if not drive:
        url = url.lstrip('/')
    return 'file:///' + drive + url

def url_to_filename(url):
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    filename = url[len('file:'):].lstrip('/')
    filename = urllib.unquote(filename)
    if _url_drive_re.match(filename):
        filename = filename[0] + ':' + filename[2:]
    else:
        filename = '/' + filename
    return filename

def get_requirement_from_url(url):
    """Get a requirement from the URL, if possible.  This looks for #egg
    in the URL"""
    link = Link(url)
    egg_info = link.egg_fragment
    if not egg_info:
        egg_info = splitext(link.filename)[0]
    return package_to_requirement(egg_info)

def package_to_requirement(package_name):
    """Translate a name like Foo-1.2 to Foo==1.3"""
    match = re.search(r'^(.*?)(-dev|-\d.*)', package_name)
    if match:
        name = match.group(1)
        version = match.group(2)
    else:
        name = package_name
        version = ''
    if version:
        return '%s==%s' % (name, version)
    else:
        return name

def is_framework_layout(path):
    """Return True if the current platform is the default Python of Mac OS X
    which installs scripts in /usr/local/bin"""
    return (sys.platform[:6] == 'darwin' and
            (path[:9] == '/Library/' or path[:16] == '/System/Library/'))

def strip_prefix(path, prefix):
    """ If ``path`` begins with ``prefix``, return ``path`` with
    ``prefix`` stripped off.  Otherwise return None."""
    prefixes = [prefix]
    # Yep, we are special casing the framework layout of MacPython here
    if is_framework_layout(sys.prefix):
        for location in ('/Library', '/usr/local'):
            if path.startswith(location):
                prefixes.append(location)
    for prefix in prefixes:
        if path.startswith(prefix):
            return prefix, path.replace(prefix + os.path.sep, '')
    return None, None

class UninstallPathSet(object):
    """A set of file paths to be removed in the uninstallation of a
    requirement."""
    def __init__(self, dist, restrict_to_prefix):
        self.paths = set()
        self._refuse = set()
        self.pth = {}
        self.prefix = os.path.normcase(os.path.realpath(restrict_to_prefix))
        self.dist = dist
        self.location = dist.location
        self.save_dir = None
        self._moved_paths = []

    def _can_uninstall(self):
        prefix, stripped = strip_prefix(self.location, self.prefix)
        if not stripped:
            logger.notify("Not uninstalling %s at %s, outside environment %s"
                          % (self.dist.project_name, self.dist.location,
                             self.prefix))
            return False
        return True

    def add(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return
        prefix, stripped = strip_prefix(os.path.normcase(path), self.prefix)
        if stripped:
            self.paths.add((prefix, stripped))
        else:
            self._refuse.add((prefix, path))

    def add_pth(self, pth_file, entry):
        prefix, stripped = strip_prefix(os.path.normcase(pth_file), self.prefix)
        if stripped:
            entry = os.path.normcase(entry)
            if stripped not in self.pth:
                self.pth[stripped] = UninstallPthEntries(os.path.join(prefix, stripped))
            self.pth[stripped].add(os.path.normcase(entry))
        else:
            self._refuse.add((prefix, pth_file))

    def compact(self, paths):
        """Compact a path set to contain the minimal number of paths
        necessary to contain all paths in the set. If /a/path/ and
        /a/path/to/a/file.txt are both in the set, leave only the
        shorter path."""
        short_paths = set()
        def sort_set(x, y):
            prefix_x, path_x = x
            prefix_y, path_y = y
            return cmp(len(path_x), len(path_y))
        for prefix, path in sorted(paths, sort_set):
            if not any([(path.startswith(shortpath) and
                         path[len(shortpath.rstrip(os.path.sep))] == os.path.sep)
                        for shortprefix, shortpath in short_paths]):
                short_paths.add((prefix, path))
        return short_paths

    def remove(self, auto_confirm=False):
        """Remove paths in ``self.paths`` with confirmation (unless
        ``auto_confirm`` is True)."""
        if not self._can_uninstall():
            return
        logger.notify('Uninstalling %s:' % self.dist.project_name)
        logger.indent += 2
        paths = sorted(self.compact(self.paths))
        try:
            if auto_confirm:
                response = 'y'
            else:
                for prefix, path in paths:
                    logger.notify(os.path.join(prefix, path))
                response = ask('Proceed (y/n)? ', ('y', 'n'))
            if self._refuse:
                logger.notify('Not removing or modifying (outside of prefix):')
                for prefix, path in self.compact(self._refuse):
                    logger.notify(os.path.join(prefix, path))
            if response == 'y':
                self.save_dir = tempfile.mkdtemp('-uninstall', 'pip-')
                for prefix, path in paths:
                    full_path = os.path.join(prefix, path)
                    new_path = os.path.join(self.save_dir, path)
                    new_dir = os.path.dirname(new_path)
                    logger.info('Removing file or directory %s' % full_path)
                    self._moved_paths.append((prefix, path))
                    os.renames(full_path, new_path)
                for pth in self.pth.values():
                    pth.remove()
                logger.notify('Successfully uninstalled %s' % self.dist.project_name)

        finally:
            logger.indent -= 2

    def rollback(self):
        """Rollback the changes previously made by remove()."""
        if self.save_dir is None:
            logger.error("Can't roll back %s; was not uninstalled" % self.dist.project_name)
            return False
        logger.notify('Rolling back uninstall of %s' % self.dist.project_name)
        for prefix, path in self._moved_paths:
            tmp_path = os.path.join(self.save_dir, path)
            real_path = os.path.join(prefix, path)
            logger.info('Replacing %s' % real_path)
            os.renames(tmp_path, real_path)
        for pth in self.pth:
            pth.rollback()

    def commit(self):
        """Remove temporary save dir: rollback will no longer be possible."""
        if self.save_dir is not None:
            shutil.rmtree(self.save_dir)
            self.save_dir = None
            self._moved_paths = []


class UninstallPthEntries(object):
    def __init__(self, pth_file):
        if not os.path.isfile(pth_file):
            raise UninstallationError("Cannot remove entries from nonexistent file %s" % pth_file)
        self.file = pth_file
        self.entries = set()
        self._saved_lines = None

    def add(self, entry):
        self.entries.add(entry)

    def remove(self):
        logger.info('Removing pth entries from %s:' % self.file)
        fh = open(self.file, 'r')
        lines = fh.readlines()
        self._saved_lines = lines
        fh.close()
        try:
            for entry in self.entries:
                logger.info('Removing entry: %s' % entry)
            try:
                lines.remove(entry + '\n')
            except ValueError:
                pass
        finally:
            pass
        fh = open(self.file, 'w')
        fh.writelines(lines)
        fh.close()

    def rollback(self):
        if self._saved_lines is None:
            logger.error('Cannot roll back changes to %s, none were made' % self.file)
            return False
        logger.info('Rolling %s back to previous state' % self.file)
        fh = open(self.file, 'w')
        fh.writelines(self._saved_lines)
        fh.close()
        return True

class FakeFile(object):
    """Wrap a list of lines in an object with readline() to make
    ConfigParser happy."""
    def __init__(self, lines):
        self._gen = (l for l in lines)

    def readline(self):
        try:
            return self._gen.next()
        except StopIteration:
            return ''
    
def splitext(path):
    """Like os.path.splitext, but take off .tar too"""
    base, ext = posixpath.splitext(path)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext

def find_command(cmd, paths=None, pathext=None):
    """Searches the PATH for the given command and returns its path"""
    if paths is None:
        paths = os.environ.get('PATH', []).split(os.pathsep)
    if isinstance(paths, basestring):
        paths = [paths]
    # check if there are funny path extensions for executables, e.g. Windows
    if pathext is None:
        pathext = os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD')
    pathext = [ext for ext in pathext.lower().split(os.pathsep)]
    # don't use extensions if the command ends with one of them
    if os.path.splitext(cmd)[1].lower() in pathext:
        pathext = ['']
    # check if we find the command on PATH
    for path in paths:
        # try without extension first
        cmd_path = os.path.join(path, cmd)
        for ext in pathext:
            # then including the extension
            cmd_path_ext = cmd_path + ext
            if os.path.exists(cmd_path_ext):
                return cmd_path_ext
        if os.path.exists(cmd_path):
            return cmd_path
    return None

class _Inf(object):
    """I am bigger than everything!"""
    def __cmp__(self, a):
        if self is a:
            return 0
        return 1
    def __repr__(self):
        return 'Inf'
Inf = _Inf()
del _Inf

if __name__ == '__main__':
    exit = main()
    if exit:
        sys.exit(exit)
