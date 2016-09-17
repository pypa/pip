from __future__ import absolute_import

import logging
import os

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """\
    Show information about pip's wheel cache.

    Subcommands:
        location: Print the location of the wheel cache."""
    actions = ["location"]
    name = "cache"
    usage = """
      %%prog [options] %s""" % "|".join(actions)
    summary = "Show information about pip's wheel cache."

    def run(self, options, args):
        if not args or args[0] not in self.actions:
            logger.warning(
                "ERROR: Please provide one of these subcommands: %s" %
                ", ".join(self.actions))
            return ERROR
        method = getattr(self, "action_%s" % args[0])
        return method(options, args[1:])

    def action_location(self, options, args):
        logger.info(os.path.join(options.cache_dir, "wheels"))
        return SUCCESS
