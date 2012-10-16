import os
import sys
from pip.basecommand import Command
from pip.commands.options import *
from pip.index import PackageFinder
from pip.log import logger
from pip.exceptions import CommandError
from pip.req import InstallRequirement, RequirementSet, parse_requirements
from pip.util import normalize_path
from pip.wheel import WheelBuilder


DEFAULT_WHEEL_DIR = os.path.join(normalize_path(os.curdir), 'wheelhouse')

class WheelCommand(Command):
    name = 'wheel'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'Build wheels from your requirements'

    def __init__(self):
        super(WheelCommand, self).__init__()
        self.parser.add_option(
            '-w', '--wheel-dir',
            dest='wheel_dir',
            metavar='DIR',
            default=DEFAULT_WHEEL_DIR,
            help='Build wheels into DIR (default %default)')
        self.parser.add_option(
            '--unpack-only',
            dest='unpack_only',
            action='store_true',
            default=False,
            help='Only unpack')
        self.parser.add_option(REQUIREMENTS)
        self.parser.add_option(FIND_LINKS)
        self.parser.add_option(INDEX_URL)
        self.parser.add_option(EXTRA_INDEX_URLS)
        self.parser.add_option(NO_INDEX)
        self.parser.add_option(USE_MIRRORS)
        self.parser.add_option(MIRRORS)
        self.parser.add_option(DOWNLOAD_CACHE)
        self.parser.add_option(BUILD_DIR)
        self.parser.add_option(
            '--build-option',
            dest='build_options',
            action='append',
            help="Extra arguments to be supplied to setup.py bdist_wheel")
        self.parser.add_option(GLOBAL_OPTIONS)

    def run(self, options, args):

        if sys.version_info < (2, 6):
             raise CommandError("'pip wheel' requires py2.6 or greater.")

        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        finder = PackageFinder(find_links=options.find_links,
                               index_urls=index_urls,
                               use_mirrors=options.use_mirrors,
                               mirrors=options.mirrors,
                               use_wheel=False)

        options.build_dir = os.path.abspath(options.build_dir)
        requirement_set = RequirementSet(
            build_dir=options.build_dir,
            src_dir=None,
            download_dir=None,
            download_cache=options.download_cache,
            ignore_installed=True)

        #parse args and/or requirements files
        for name in args:
            if name.endswith(".whl"):
                logger.notify("ignoring %s" % name)
                continue
            requirement_set.add_requirement(
                InstallRequirement.from_line(name, None))
        for filename in options.requirements:
            for req in parse_requirements(filename, finder=finder, options=options):
                if req.editable or (req.name is None and req.url.endswith(".whl")):
                    logger.notify("ignoring %s" % req.url)
                    continue
                requirement_set.add_requirement(req)

        #fail if no requirements
        if not requirement_set.has_requirements:
            opts = {'name': self.name}
            msg = ('You must give at least one requirement '
                   'to %(name)s (see "pip help %(name)s")' % opts)
            logger.error(msg)
            return

        #if unpack-only, just prepare and return
        #'pip wheel' probably shouldn't be offering this? 'pip unpack'?
        if options.unpack_only:
            requirement_set.prepare_files(finder)
            return

        #build wheels
        wb = WheelBuilder(
            requirement_set,
            finder,
            options.wheel_dir,
            build_options = options.build_options or [],
            global_options = options.global_options or []
            )
        wb.build()

        requirement_set.cleanup_files()


WheelCommand()
