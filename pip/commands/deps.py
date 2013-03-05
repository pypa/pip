import os
import sys
from pip.req import InstallRequirement, RequirementSet, parse_requirements
from pip.log import logger
from pip.locations import build_prefix, src_prefix
from pip.basecommand import Command, ERROR, SUCCESS
from pip.index import PackageFinder
from pip.cmdoptions import make_option_group, index_group


class DependenciesCommand(Command):
    """
    Resolve package dependencies from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports resolving from "requirements files", which provide
    an easy way to specify a whole environment to be installed.

    See http://www.pip-installer.org for details on VCS url formats and
    requirements files.
    """
    name = 'deps'

    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Resolve dependencies for packages.'
    bundle = False

    def __init__(self, *args, **kw):
        super(DependenciesCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-e', '--editable',
            dest='editables',
            action='append',
            default=[],
            metavar='path/url',
            help='Install a project in editable mode (i.e. setuptools "develop mode") from a local project path or a VCS url.')

        cmd_opts.add_option(
            '-r', '--requirement',
            dest='requirements',
            action='append',
            default=[],
            metavar='file',
            help='Install from the given requirements file. '
            'This option can be used multiple times.')

        index_opts = make_option_group(index_group, self.parser)

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

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
        options.no_install = True

        options.build_dir = os.path.abspath(build_prefix)
        options.src_dir = os.path.abspath(src_prefix)
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        finder = self._build_package_finder(options, index_urls)

        requirement_set = RequirementSet(
            build_dir=options.build_dir,
            src_dir=options.src_dir,
            download_dir=None,
            ignore_installed=True,
            force_reinstall=True)

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
            return ERROR

        requirement_set.prepare_files(finder)

        requirements = '\n'.join(
            ['%s==%s' % (req.name, req.installed_version) for req in
                requirement_set.successfully_downloaded])

        if requirements:
            requirement_set.cleanup_files()
            sys.stdout.write(requirements + '\n')

        return SUCCESS

    def setup_logging(self):
        # Avoid download progress on stdout
        logger.move_stdout_to_stderr()
