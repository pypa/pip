
import os
import sys

from pip.req import InstallRequirement, RequirementSet
from pip.req import parse_requirements
from pip.log import logger
from pip.locations import build_prefix, src_prefix
from pip.basecommand import Command
from pip.index import PackageFinder
from pip.exceptions import InstallationError


class InstallCommand(Command):
    name = 'install'
    usage = '%prog [options] <package> [<package> ...]'
    summary = 'install packages'
    bundle = False

    def __init__(self, *args, **kw):
        super(InstallCommand, self).__init__(*args, **kw)

        cmdadd = self.command_group.add_option

        cmdadd(
			'-e', '--editable',
            dest='editables',
            action='append',
            default=[],
            metavar='VCS+REPOS_URL[@REV]#egg=PACKAGE',
            help='install a package directly from a checkout. Source will be checked '
            'out into src/PACKAGE (lower-case) and installed in-place (using '
            'setup.py develop). You can run this on an existing directory/checkout (like '
            'pip install -e src/mycheckout). This option may be provided multiple times. '
            'Possible values for VCS are: svn, git, hg and bzr.')

        cmdadd( '-r', '--requirement',
                dest='requirements',
                action='append',
                default=[],
                metavar='path',
                help='install packages in requirements file')

        cmdadd( '-f', '--find-links',
                dest='find_links',
                action='append',
                default=[],
                metavar='url',
                help='url to look for packages at')

        cmdadd( '-i', '--index-url', '--pypi-url',
                dest='index_url',
                metavar='url',
                default='http://pypi.python.org/simple/',
                help='base url of python package index')

        cmdadd( '--extra-index-url',
                dest='extra_index_urls',
                metavar='url',
                action='append',
                default=[],
                help='extra url of package indexes to use in addition to --index-url')

        cmdadd( '--no-index',
                dest='no_index',
                action='store_true',
                default=False,
                help='ignore package index')
                #help='ignore package index (only looking at --find-links URLs instead)')

        cmdadd( '-M', '--use-mirrors',
				dest='use_mirrors',
				action='store_true',
				default=False,
				help='use pypi mirrors as a fallback')

        cmdadd( '--mirrors',
                dest='mirrors',
                metavar='url',
                action='append',
                default=[],
                help='mirror urls to query when --use-mirrors')

		# TODO: print just two, suppress the rest
        cmdadd('-b', '--build', '--build-dir', '--build-directory',
            dest='build_dir',
            metavar='dir',
            default=build_prefix,
            help='unpack packages into <dir> and build from there')

        cmdadd( '-d', '--download', '--download-dir', '--download-directory',
                dest='download_dir',
                metavar='dir',
                default=None,
                help='download packages into <dir> instead of installing them')

        cmdadd( '--download-cache',
                dest='download_cache',
                metavar='dir',
                default=None,
                help='cache downloaded packages in DIR')

        cmdadd( '--src', '--source', '--source-dir', '--source-directory',
                dest='src_dir',
                metavar='dir',
                default=src_prefix,
                help='check out --editable packages into <dir>')

        cmdadd( '-U', '--upgrade',
                dest='upgrade',
                action='store_true',
                help='upgrade all packages to the newest available version')

        cmdadd( '--force-reinstall',
                dest='force_reinstall',
                action='store_true',
                help='reinstall all packages even if they are already up-to-date.')

        cmdadd( '-I', '--ignore-installed',
                dest='ignore_installed',
                action='store_true',
                help='ignore installed packages (reinstalling instead)')

        cmdadd( '--no-deps', '--no-dependencies',
                dest='ignore_dependencies',
                action='store_true',
                default=False,
                help='ignore package dependencies')

        cmdadd( '--no-install',
                dest='no_install',
                action='store_true',
                help="download and unpack, but don't install")

        cmdadd( '--no-download',
                dest='no_download',
                action="store_true",
                help="install only download packages (completes --no-install)")

        cmdadd( '--install-option',
                dest='install_options',
                action='append',
				metavar='options',
                help="extra arguments to be supplied to the setup.py install "
                "command (use like --install-option=\"--install-scripts=/usr/local/bin\").  "
                "Use multiple --install-option options to pass multiple options to setup.py install.  "
                "If you are using an option with a directory path, be sure to use absolute path.")

        cmdadd( '--global-option',
                dest='global_options',
				metavar='options',
                action='append',
                help="extra global options to be supplied to the setup.py"
                "call before the install command")

        cmdadd( '--user',
                dest='use_user_site',
                action='store_true',
                help='install to user-site')

        # TODO: lame!
        self.parser.add_option_group(self.command_group)

    def _build_package_finder(self, options, index_urls):
        """
        Create a package finder appropriate to this install command.
        This method is meant to be overridden by subclasses, not
        called directly.
        """
        return PackageFinder(find_links=options.find_links,
                             index_urls=index_urls,
                             use_mirrors=options.use_mirrors,
                             mirrors=options.mirrors)

    def run(self, options, args):
        if options.download_dir:
            options.no_install = True
            options.ignore_installed = True
        options.build_dir = os.path.abspath(options.build_dir)
        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
            install_options.append('--user')
        global_options = options.global_options or []
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        finder = self._build_package_finder(options, index_urls)

        requirement_set = RequirementSet(
            build_dir=options.build_dir,
            src_dir=options.src_dir,
            download_dir=options.download_dir,
            download_cache=options.download_cache,
            upgrade=options.upgrade,
            ignore_installed=options.ignore_installed,
            ignore_dependencies=options.ignore_dependencies,
            force_reinstall=options.force_reinstall)
        for name in args:
            requirement_set.add_requirement(
                InstallRequirement.from_line(name, None))
        for name in options.editables:
            requirement_set.add_requirement(
                InstallRequirement.from_editable(name, default_vcs=options.default_vcs))
        for filename in options.requirements:
            for req in parse_requirements(filename, finder=finder, options=options):
                requirement_set.add_requirement(req)
        if not requirement_set.has_requirements:
            opts = {'name': self.name}
            if options.find_links:
                msg = ('You must give at least one requirement to %(name)s '
                       '(maybe you meant "pip %(name)s %(links)s"?)' %
                       dict(opts, links=' '.join(options.find_links)))
            else:
                msg = ('You must give at least one requirement '
                       'to %(name)s (see "pip help %(name)s")' % opts)
            logger.warn(msg)
            return

        if (options.use_user_site and
            sys.version_info < (2, 6)):
            raise InstallationError('--user is only supported in Python version 2.6 and newer')

        import setuptools
        if (options.use_user_site and
            requirement_set.has_editables and
            not getattr(setuptools, '_distribute', False)):

            raise InstallationError('--user --editable not supported with setuptools, use distribute')

        if not options.no_download:
            requirement_set.prepare_files(finder, force_root_egg_info=self.bundle, bundle=self.bundle)
        else:
            requirement_set.locate_files()

        if not options.no_install and not self.bundle:
            requirement_set.install(install_options, global_options)
            installed = ' '.join([req.name for req in
                                  requirement_set.successfully_installed])
            if installed:
                logger.notify('Successfully installed %s' % installed)
        elif not self.bundle:
            downloaded = ' '.join([req.name for req in
                                   requirement_set.successfully_downloaded])
            if downloaded:
                logger.notify('Successfully downloaded %s' % downloaded)
        elif self.bundle:
            requirement_set.create_bundle(self.bundle_filename)
            logger.notify('Created bundle in %s' % self.bundle_filename)
        # Clean up
        if not options.no_install:
            requirement_set.cleanup_files(bundle=self.bundle)
        return requirement_set

