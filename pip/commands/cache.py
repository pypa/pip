from __future__ import absolute_import

import logging
import os
from os.path import realpath
import textwrap

from pip.basecommand import Command
from pip.exceptions import CommandError
from pip.status_codes import SUCCESS, ERROR
from pip.utils import format_size
from pip.utils.filesystem import tree_statistics, find_files


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """\
    Operate on pip's caches.

    Subcommands:
        info: Show information about the caches.
        list (wheel cache only): List wheels stored in the cache.
        rm <filename> (wheel cache only): Remove one or more wheels from the cache.
    """  # noqa
    actions = ["info", "list", "rm"]
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
            raise CommandError(
                "Please provide one of these subcommands: %s" %
                ", ".join(self.actions)
            )
        method = getattr(self, "action_%s" % args[0])
        return method(options, args[1:])

    def get_cache_location(self, cache_root, cache_type):
        location = cache_root
        suffix = {"wheel": "wheels", "http": "http"}
        if cache_type != "all":
            location = os.path.join(location, suffix[cache_type])
        return location

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
                   Files: %s
                   Size: %s""" %
                (name[cache_type], location, stats["files"],
                 format_size(stats["size"]))
            ))
        logger.info((os.linesep * 2).join(result))
        return SUCCESS

    def action_list(self, options, args):
        if options.type != "wheel":
            raise CommandError(
                "pip cache list only operates on the wheel cache.")
        cache_location = self.get_cache_location(options.cache_dir, "wheel")
        wheels = [os.path.basename(f) for f in
                  find_files(cache_location, "*.whl")]
        wheels.sort()
        logger.info(os.linesep.join(wheels))

    def action_rm(self, options, args):
        if options.type != "wheel":
            raise CommandError(
                "pip cache rm only operates on the wheel cache.")
        if len(args) == 0:
            raise CommandError(
                "Must specify the filename of (a) wheel(s) to remove.")
        cache_location = self.get_cache_location(options.cache_dir, "wheel")
        cache_realpath = realpath(cache_location)
        value = SUCCESS
        for target in args:
            matches = find_files(cache_location, target)
            if not matches:
                logger.warning("No match found for %s" % target)
                value = ERROR
                continue
            for match in matches:
                # protect against symlink attacks
                if (os.path.commonprefix([cache_realpath, realpath(match)]) !=
                        cache_realpath):
                    logger.warning(
                        "Did not remove %s because it is not a child of the "
                        "wheel cache." % realpath(match))
                    value = ERROR
                    continue
                try:
                    os.unlink(match)
                except OSError as e:
                    logger.warning(
                        "Could not remove %s; %s" % (match, e))
                    value = ERROR
                else:
                    logger.info("Removed %s" % match)

        return value
