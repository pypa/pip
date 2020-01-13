from __future__ import absolute_import

import logging
import os
import textwrap

import pip._internal.utils.filesystem as filesystem
from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from optparse import Values
    from typing import Any, List


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """
        Inspect and manage pip's cache.

        Subcommands:

        info:
            Show information about the cache.
        list:
            List filenames of packages stored in the cache.
        remove:
            Remove one or more package from the cache.
        purge:
            Remove all items from the cache.

        <pattern> can be a glob expression or a package name.
    """

    usage = """
        %prog info
        %prog list [name]
        %prog remove <pattern>
        %prog purge
    """

    def __init__(self, *args, **kw):
        # type: (*Any, **Any) -> None
        super(CacheCommand, self).__init__(*args, **kw)

    def run(self, options, args):
        # type: (Values, List[Any]) -> int
        handlers = {
            "info": self.get_cache_info,
            "list": self.list_cache_items,
            "remove": self.remove_cache_items,
            "purge": self.purge_cache,
        }

        # Determine action
        if not args or args[0] not in handlers:
            logger.error("Need an action ({}) to perform.".format(
                ", ".join(sorted(handlers)))
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def get_cache_info(self, options, args):
        # type: (Values, List[Any]) -> None
        num_packages = len(self._find_wheels(options, '*'))

        cache_location = self._wheels_cache_dir(options)
        cache_size = filesystem.friendly_directory_size(cache_location)

        message = textwrap.dedent("""
            Cache info:
              Location: {location}
              Packages: {package_count}
              Size:     {size}
        """).format(
            location=cache_location,
            package_count=num_packages,
            size=cache_size,
        ).strip()

        logger.info(message)

    def list_cache_items(self, options, args):
        # type: (Values, List[Any]) -> None
        if len(args) > 1:
            raise CommandError('Too many arguments')

        if args:
            pattern = args[0]
        else:
            pattern = '*'

        files = self._find_wheels(options, pattern)

        if not files:
            logger.info('Nothing cached.')
            return

        results = []
        for filename in files:
            wheel = os.path.basename(filename)
            size = filesystem.friendly_file_size(filename)
            results.append(' - {} ({})'.format(wheel, size))
        logger.info('Cache contents:\n')
        logger.info('\n'.join(sorted(results)))

    def remove_cache_items(self, options, args):
        # type: (Values, List[Any]) -> None
        if len(args) > 1:
            raise CommandError('Too many arguments')

        if not args:
            raise CommandError('Please provide a pattern')

        files = self._find_wheels(options, args[0])
        if not files:
            raise CommandError('No matching packages')

        for filename in files:
            os.unlink(filename)
            logger.debug('Removed %s', filename)
        logger.info('Removed %s file(s)', len(files))

    def purge_cache(self, options, args):
        # type: (Values, List[Any]) -> None
        if args:
            raise CommandError('Too many arguments')

        return self.remove_cache_items(options, ['*'])

    def _wheels_cache_dir(self, options):
        # type: (Values) -> str
        return os.path.join(options.cache_dir, 'wheels')

    def _find_wheels(self, options, pattern):
        # type: (Values, str) -> List[str]
        wheel_dir = self._wheels_cache_dir(options)
        return filesystem.find_files(wheel_dir, pattern + '*.whl')
