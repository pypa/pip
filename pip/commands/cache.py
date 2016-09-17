from __future__ import absolute_import

import logging
import os

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """\
    Operate on pip's caches.

    Subcommands:
        location: Print the location of the cache."""
    actions = ["location"]
    name = "cache"
    usage = """
      %%prog [options] %s""" % "|".join(actions)
    summary = "Operate on pip's caches."

    def __init__(self, *args, **kw):
        super(CacheCommand, self).__init__(*args, **kw)

        cache_types = ["all", "http", "wheel"]

        self.cmd_opts.add_option(
            "--type", "-t",
            choices=cache_types,
            default="wheel",
            help="The cache upon which to operate: %s (default: %%default)" %
                 ", ".join(cache_types)
        )
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        if not args or args[0] not in self.actions:
            logger.warning(
                "ERROR: Please provide one of these subcommands: %s" %
                ", ".join(self.actions))
            return ERROR
        method = getattr(self, "action_%s" % args[0])
        return method(options, args[1:])

    def action_location(self, options, args):
        location = options.cache_dir
        suffix = {"wheel": "wheels", "http": "http"}
        if options.type != "all":
            location = os.path.join(location, suffix[options.type])
        logger.info(location)
        return SUCCESS
