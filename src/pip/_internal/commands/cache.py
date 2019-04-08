from __future__ import absolute_import

import logging
import os
import textwrap

from pip._internal.cli.base_command import Command
from pip._internal.exceptions import CommandError
from pip._internal.utils.filesystem import find_files

logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's caches.

    Subcommands:
        info:
            Show information about the caches.
        list [name]:
            List filenames of packages stored in the cache.
        remove <pattern>:
            Remove one or more package from the cache.
            `pattern` can be a glob expression or a package name.
        purge:
            Remove all items from the cache.
    """
    actions = ['info', 'list', 'remove', 'purge']
    name = 'cache'
    usage = """
      %prog <command>"""
    summary = "View and manage which packages are available in pip's caches."

    def __init__(self, *args, **kw):
        super(CacheCommand, self).__init__(*args, **kw)

    def run(self, options, args):
        if not args:
            raise CommandError('Please provide a subcommand.')

        if args[0] not in self.actions:
            raise CommandError('Invalid subcommand: %s' % args[0])

        self.wheel_dir = os.path.join(options.cache_dir, 'wheels')

        method = getattr(self, 'action_%s' % args[0])
        return method(options, args[1:])

    def action_info(self, options, args):
        format_args = (options.cache_dir, len(self.find_wheels('*.whl')))
        result = textwrap.dedent(
            """\
            Cache info:
              Location: %s
              Packages: %s""" % format_args
        )
        logger.info(result)

    def action_list(self, options, args):
        if args and args[0]:
            pattern = args[0]
        else:
            pattern = '*'

        files = self.find_wheels(pattern)
        wheels = map(self._wheel_info, files)
        wheels = sorted(set(wheels))

        if not wheels:
            logger.info('Nothing is currently cached.')
            return

        result = 'Current cache contents:\n'
        for wheel in wheels:
            result += ' - %s\n' % wheel
        logger.info(result.strip())

    def action_remove(self, options, args):
        if not args:
            raise CommandError('Please provide a pattern')

        files = self.find_wheels(args[0])
        if not files:
            raise CommandError('No matching packages')

        wheels = map(self._wheel_info, files)
        result = 'Removing cached wheels for:\n'
        for wheel in wheels:
            result += '- %s\n' % wheel

        for filename in files:
            os.unlink(filename)
            logger.debug('Removed %s', filename)
        logger.info('Removed %s files', len(files))

    def action_purge(self, options, args):
        return self.action_remove(options, '*')

    def _wheel_info(self, path):
        filename = os.path.splitext(os.path.basename(path))[0]
        name, version = filename.split('-')[0:2]
        return '%s-%s' % (name, version)

    def find_wheels(self, pattern):
        return find_files(self.wheel_dir, pattern + '-*.whl')
