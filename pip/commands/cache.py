from __future__ import absolute_import

import fnmatch
import logging
import os
from os.path import basename, isdir, islink
import textwrap

from pip.basecommand import Command
from pip.exceptions import CommandError
from pip.status_codes import SUCCESS, ERROR
from pip.utils import format_size, rmtree
from pip.utils.filesystem import tree_statistics, find_files
from pip.wheel import Wheel, InvalidWheelFilename
from pip._vendor.pkg_resources import safe_name


logger = logging.getLogger(__name__)


class CacheCommand(Command):
    """\
    Operate on pip's caches.

    Subcommands:
        info:
            Show information about the caches.
        list (wheel cache only):
            List filenames of wheels stored in the cache.
        rm <pattern|packagename> (wheel cache only):
            Remove one or more wheels from the cache. `rm` accepts one or more
            package names, filenames, or shell glob expressions matching filenames.
        purge:
            Remove all items from the cache.
    """  # noqa
    actions = ["info", "list", "rm", "purge"]
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

    @staticmethod
    def get_cache_location(cache_root, cache_type):
        location = cache_root
        suffix = {"wheel": "wheels", "http": "http"}
        if cache_type != "all":
            location = os.path.join(location, suffix[cache_type])
        return location

    @staticmethod
    def wheels_matching(cache_location, pattern):
        """Returns a list of absolute filenames of wheels with filenames
        matching `pattern`. A pattern may be:
            * the name of a package
            * a shell glob expression matching the basename of the wheel
            * an exact basename
        """
        shell_metachars = '*?'
        if (any(m in pattern for m in shell_metachars) or
                pattern.endswith(".whl")):
            matches = find_files(cache_location, pattern)
            matches = fnmatch.filter(matches, "*.whl")
        else:
            wheels = find_files(cache_location, "*.whl")
            pkgname = safe_name(pattern).lower()
            matches = []
            for filename in wheels:
                try:
                    wheel = Wheel(basename(filename))
                except InvalidWheelFilename:
                    continue
                if wheel.name.lower() == pkgname:
                    matches.append(filename)
        return matches

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
        wheels = [basename(f) for f in find_files(cache_location, "*.whl")]
        wheels.sort()
        if wheels:
            logger.info(os.linesep.join(wheels))
        return SUCCESS

    def action_rm(self, options, args):
        if options.type != "wheel":
            raise CommandError(
                "pip cache rm only operates on the wheel cache.")
        if len(args) == 0:
            raise CommandError(
                "Must specify the filename of (a) wheel(s) to remove.")
        cache_location = self.get_cache_location(options.cache_dir, "wheel")
        value = SUCCESS
        for pattern in args:
            matches = self.wheels_matching(cache_location, pattern)
            if not matches:
                logger.info("No match found for %s" % pattern)
                continue
            for match in matches:
                try:
                    os.unlink(match)
                except OSError as e:
                    logger.warning(
                        "Could not remove %s; %s" % (match, e))
                    value = ERROR
                else:
                    logger.info("Removed %s" % match)
        return value

    def action_purge(self, options, args):
        caches = ["http", "wheel"] if options.type == "all" else [options.type]
        value = SUCCESS
        for cache_type in caches:
            cache_location = self.get_cache_location(
                options.cache_dir, cache_type)
            if islink(cache_location) or not isdir(cache_location):
                logger.info("%s is not a directory; skipping"
                            % cache_location)
                continue
            try:
                rmtree(cache_location)
            except OSError as e:
                logger.warning("Could not remove %s; %s" % (cache_location, e))
                value = ERROR
            else:
                logger.info("Removed %s" % cache_location)
        return value
