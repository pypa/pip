from __future__ import absolute_import

import logging
import os
import textwrap

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR
from pip.utils import format_size
from pip.utils.filesystem import tree_statistics


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """\
    Operate on pip's caches.

    Subcommands:
        location: Print the location of the cache.
        info: Show statistics on the cache."""
    actions = ["location", "info"]
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

    def get_cache_location(self, cache_root, cache_type):
        location = cache_root
        suffix = {"wheel": "wheels", "http": "http"}
        if cache_type != "all":
            location = os.path.join(location, suffix[cache_type])
        return location

    def action_location(self, options, args):
        logger.info(self.get_cache_location(options.cache_dir, options.type))
        return SUCCESS

    def action_info(self, options, args):
        caches = ["http", "wheel"] if options.type == "all" else [options.type]
        result = []
        for cache_type in caches:
            location = self.get_cache_location(options.cache_dir, cache_type)
            stats = tree_statistics(location)
            name = {"wheel": "Wheel cache", "http": "HTTP cache"}
            result.append(textwrap.dedent(
                """\
                %s info:
                   Location: %s
                   Number of files: %s
                   Size: %s""" %
                (name[cache_type], location, stats["files"],
                 format_size(stats["size"]))
            ))
        logger.info("\n\n".join(result))
        return SUCCESS
