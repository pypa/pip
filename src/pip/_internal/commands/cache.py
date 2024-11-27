import fnmatch
import os
import re
import textwrap
from optparse import Values
from typing import Any, List

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import filesystem
from pip._internal.utils.logging import getLogger

logger = getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's wheel cache.

    Subcommands:

    - dir: Show the cache directory.
    - info: Show information about the cache.
    - list: List filenames of packages stored in the cache.
    - remove: Remove one or more package from the cache.
    - purge: Remove all items from the cache.

    ``<pattern>`` can be a glob expression or a package name.
    """

    ignore_require_venv = True
    usage = """
        %prog dir
        %prog info
        %prog list [<pattern>] [--format=[human, abspath]]
        %prog remove <pattern>
        %prog purge
    """

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--format",
            action="store",
            dest="list_format",
            default="human",
            choices=("human", "abspath"),
            help="Select the output format among: human (default) or abspath",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "dir": self.get_cache_dir,
            "info": self.get_cache_info,
            "list": self.list_cache_items,
            "remove": self.remove_cache_items,
            "purge": self.purge_cache,
        }

        if not options.cache_dir:
            logger.error("pip cache commands can not function since cache is disabled.")
            return ERROR

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
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

    def get_cache_dir(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        logger.info(options.cache_dir)

    def get_cache_info(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        num_http_files = len(self._find_http_files(options))
        num_packages = len(self._find_wheels(options, "*"))

        http_cache_location = self._cache_dir(options, "http-v2")
        old_http_cache_location = self._cache_dir(options, "http")
        wheels_cache_location = self._cache_dir(options, "wheels")
        http_cache_size = filesystem.format_size(
            filesystem.directory_size(http_cache_location)
            + filesystem.directory_size(old_http_cache_location)
        )
        wheels_cache_size = filesystem.format_directory_size(wheels_cache_location)

        message = (
            textwrap.dedent(
                """
                    Package index page cache location (pip v23.3+): {http_cache_location}
                    Package index page cache location (older pips): {old_http_cache_location}
                    Package index page cache size: {http_cache_size}
                    Number of HTTP files: {num_http_files}
                    Locally built wheels location: {wheels_cache_location}
                    Locally built wheels size: {wheels_cache_size}
                    Number of locally built wheels: {package_count}
                """  # noqa: E501
            )
            .format(
                http_cache_location=http_cache_location,
                old_http_cache_location=old_http_cache_location,
                http_cache_size=http_cache_size,
                num_http_files=num_http_files,
                wheels_cache_location=wheels_cache_location,
                package_count=num_packages,
                wheels_cache_size=wheels_cache_size,
            )
            .strip()
        )

        logger.info(message)

    def list_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if args:
            pattern = args[0]
        else:
            pattern = "*"

        files = self._find_wheels(options, pattern)
        if options.list_format == "human":
            self.format_for_human(files)
        else:
            self.format_for_abspath(files)

    def format_for_human(self, files: List[str]) -> None:
        if not files:
            logger.info("No locally built wheels cached.")
            return

        results = []
        for filename in files:
            wheel = os.path.basename(filename)
            size = filesystem.format_file_size(filename)
            results.append(f" - {wheel} ({size})")
        logger.info("Cache contents:\n")
        logger.info("\n".join(sorted(results)))

    def format_for_abspath(self, files: List[str]) -> None:
        if files:
            logger.info("\n".join(sorted(files)))

    def remove_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if not args:
            raise CommandError("Please provide a pattern")

        files = self._find_wheels(options, args[0])

        no_matching_msg = "No matching packages"
        if args[0] == "*":
            # Only fetch http files if no specific pattern given
            files += self._find_http_files(options)
        else:
            # Add the pattern to the log message
            no_matching_msg += f' for pattern "{args[0]}"'

        if not files:
            logger.warning(no_matching_msg)

        for filename in files:
            os.unlink(filename)
            logger.verbose("Removed %s", filename)
        logger.info("Files removed: %s", len(files))

    def purge_cache(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        return self.remove_cache_items(options, ["*"])

    def _cache_dir(self, options: Values, subdir: str) -> str:
        return os.path.join(options.cache_dir, subdir)

    def _find_http_files(self, options: Values) -> List[str]:
        old_http_dir = self._cache_dir(options, "http")
        new_http_dir = self._cache_dir(options, "http-v2")
        return filesystem.find_files(old_http_dir, "*") + filesystem.find_files(
            new_http_dir, "*"
        )

    def _find_wheels(self, options: Values, pattern: str) -> List[str]:
        wheel_dir = self._cache_dir(options, "wheels")

        # The wheel filename format, as originally specified in PEP 427, is:
        #     {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        #
        # Additionally, non-alphanumeric values in the distribution are
        # normalized to underscores (_), meaning hyphens can never occur
        # before `-{version}`.
        #
        # Given that information:
        # - If the pattern we're given is not a glob:
        #   + We attempt project name normalization such that pyyaml matches PyYAML,
        #     etc. as outlined here:
        #     https://packaging.python.org/specifications/name-normalization.
        #     The one difference is we normalize non-alphanumeric to `_` instead of `-`
        #     since that is how the wheel filename components are normalized
        #     (facepalm).
        #   + If the pattern we're given contains a hyphen (-), the user is providing
        #     at least the version. Thus, we can just append `*.whl` to match the rest
        #     of it if it doesn't already glob to the end of the wheel file name.
        #   + If the pattern we're given is not a glob and doesn't contain a
        #     hyphen (-), the user is only providing the name. Thus, we append `-*.whl`
        #     to match the hyphen before the version, followed by anything else.
        # - If the pattern is a glob, we ensure `*.whl` is appended if needed but
        #   cowardly do not attempt glob parsing / project name normalization. The user
        #   is on their own at that point.
        #
        # PEP 427: https://www.python.org/dev/peps/pep-0427/
        # And: https://packaging.python.org/specifications/binary-distribution-format/
        uses_glob_patterns = any(
            glob_pattern_char in pattern for glob_pattern_char in ("[", "*", "?")
        )
        if not uses_glob_patterns:
            project_name, sep, rest = pattern.partition("-")
            # N.B.: This only normalizes non-alphanumeric characters in the name, which
            # is 1/2 the job. Stripping case sensitivity is the other 1/2 and is
            # handled below in the conversion from a glob to a regex executed with the
            # IGNORECASE flag active.
            partially_normalized_project_name = re.sub(r"[^\w.]+", "_", project_name)
            if not sep:
                sep = "-"
            pattern = f"{partially_normalized_project_name}{sep}{rest}"

        if not pattern.endswith((".whl", "*")):
            pattern = f"{pattern}*.whl"

        regex = fnmatch.translate(pattern)

        return [
            os.path.join(root, filename)
            for root, _, files in os.walk(wheel_dir)
            for filename in files
            if re.match(regex, filename, flags=re.IGNORECASE)
        ]
