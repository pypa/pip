from __future__ import absolute_import

import logging
import os
import textwrap

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils.filesystem import find_files
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from optparse import Values
    from typing import Any, List


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """Inspect and manage pip's caches.

        Subcommands:

        info: Show information about the caches.
        list: List filenames of packages stored in the cache.
        remove: Remove one or more package from the cache.
        purge: Remove all items from the cache.

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

        results = textwrap.dedent("""\
            Cache info:
              Location: %s
              Packages: %s""" % (options.cache_dir, num_packages)
        )

        logger.info(results)

    def list_cache_items(self, options, args):
        # type: (Values, List[Any]) -> None
        if args and args[0]:
            pattern = args[0]
        else:
            pattern = '*'

        files = self._find_wheels(options, pattern)
        wheels = sorted(set(map(lambda f: os.path.basename(f), files)))

        if not wheels:
            logger.info('Nothing is currently cached.')
            return

        result = 'Current cache contents:\n'
        for wheel in wheels:
            result += ' - %s\n' % wheel
        logger.info(result.strip())

    def remove_cache_items(self, options, args):
        # type: (Values, List[Any]) -> None
        if not args:
            raise CommandError('Please provide a pattern')

        files = self._find_wheels(options, args[0])
        if not files:
            raise CommandError('No matching packages')

        for filename in files:
            os.unlink(filename)
            logger.debug('Removed %s', filename)
        logger.info('Removed %s files', len(files))

    def purge_cache(self, options, args):
        # type: (Values, List[Any]) -> None
        return self.remove_cache_items(options, ['*'])

    def _find_wheels(self, options, pattern):
        # type: (Values, str) -> List[str]
        wheel_dir = os.path.join(options.cache_dir, 'wheels')
        return find_files(wheel_dir, pattern + '-*.whl')
