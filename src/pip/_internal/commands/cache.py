import os
import textwrap
from optparse import Values
from typing import TYPE_CHECKING, Callable

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import filesystem
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import format_size

if TYPE_CHECKING:
    # Only for type checking; avoids importing network-related modules at runtime
    from pip._vendor.cachecontrol.serialize import Serializer  # noqa: F401
    from pip._vendor.requests import Request  # noqa: F401

logger = getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's wheel and HTTP cache.

    Subcommands:

    - dir: Show the cache directory.
    - info: Show information about the cache.
    - list: List cached packages (wheels and HTTP cached packages).
    - remove: Remove one or more package from the cache.
    - purge: Remove all items from the cache.

    ``<pattern>`` can be a glob expression or a package name.
    """

    ignore_require_venv = True
    usage = """
        %prog dir
        %prog info
        %prog list [<pattern>] [--format=[human, abspath]]
            [--cache-type=[all, wheels, http]]
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

        self.cmd_opts.add_option(
            "--cache-type",
            action="store",
            dest="cache_type",
            default="all",
            choices=("all", "wheels", "http"),
            help="Select which cache to list: all (default), wheels (locally built), "
            "or http (downloaded packages)",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def handler_map(self) -> dict[str, Callable[[Values, list[str]], None]]:
        return {
            "dir": self.get_cache_dir,
            "info": self.get_cache_info,
            "list": self.list_cache_items,
            "remove": self.remove_cache_items,
            "purge": self.purge_cache,
        }

    def run(self, options: Values, args: list[str]) -> int:
        handler_map = self.handler_map()

        if not options.cache_dir:
            logger.error("pip cache commands can not function since cache is disabled.")
            return ERROR

        # Determine action
        if not args or args[0] not in handler_map:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handler_map)),
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handler_map[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def get_cache_dir(self, options: Values, args: list[str]) -> None:
        if args:
            raise CommandError("Too many arguments")

        logger.info(options.cache_dir)

    def get_cache_info(self, options: Values, args: list[str]) -> None:
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

    def list_cache_items(self, options: Values, args: list[str]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        pattern = args[0] if args else "*"

        # Collect wheel files and HTTP cached packages based on cache_type option
        wheel_files: list[str] = []
        http_packages: list[tuple[str, str, str]] = []

        if options.cache_type in ("all", "wheels"):
            wheel_files = self._find_wheels(options, pattern)

        if options.cache_type in ("all", "http"):
            http_packages = self._get_http_cached_packages(options, pattern)

        if options.list_format == "human":
            self.format_for_human_combined(wheel_files, http_packages)
        else:
            self.format_for_abspath_combined(wheel_files, http_packages)

    def format_for_human(self, files: list[str]) -> None:
        if not files:
            logger.info("No cached packages.")
            return

        results = []
        for filename in files:
            wheel = os.path.basename(filename)
            size = filesystem.format_file_size(filename)
            results.append(f" - {wheel} ({size})")
        logger.info("Cache contents:\n")
        logger.info("\n".join(sorted(results)))

    def format_for_abspath(self, files: list[str]) -> None:
        if files:
            logger.info("\n".join(sorted(files)))

    def format_for_human_combined(
        self, wheel_files: list[str], http_packages: list[tuple[str, str, str]]
    ) -> None:
        """Format both wheel files and HTTP cached packages
        for human readable output."""
        if not wheel_files and not http_packages:
            logger.info("No cached packages.")
            return

        results: list[str] = []

        # Add wheel files
        for filename in wheel_files:
            wheel = os.path.basename(filename)
            size_str = filesystem.format_file_size(filename)
            results.append(f" - {wheel} ({size_str})")

        # Add HTTP cached packages
        for project, version, file_path in http_packages:
            # Create a wheel-like name for display
            wheel_name = f"{project}-{version}-py3-none-any.whl"

            # Calculate size of both header and body files
            size = 0
            try:
                size += os.path.getsize(file_path)
                body_path = file_path + ".body"
                if os.path.exists(body_path):
                    size += os.path.getsize(body_path)
            except OSError:
                pass

            size_str = filesystem.format_size(size)
            results.append(f" - {wheel_name} ({size_str}) [HTTP cached]")

        logger.info("Cache contents:\n")
        logger.info("\n".join(sorted(results)))

    def format_for_abspath_combined(
        self, wheel_files: list[str], http_packages: list[tuple[str, str, str]]
    ) -> None:
        """Format both wheel files and HTTP cached packages for absolute path output."""
        all_paths = []

        # Add wheel file paths
        all_paths.extend(wheel_files)

        # Add HTTP cache file paths
        for _, _, file_path in http_packages:
            all_paths.append(file_path)

        if all_paths:
            logger.info("\n".join(sorted(all_paths)))

    def remove_cache_items(self, options: Values, args: list[str]) -> None:
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

        bytes_removed = 0
        for filename in files:
            bytes_removed += os.stat(filename).st_size
            os.unlink(filename)
            logger.verbose("Removed %s", filename)
        logger.info("Files removed: %s (%s)", len(files), format_size(bytes_removed))

    def purge_cache(self, options: Values, args: list[str]) -> None:
        if args:
            raise CommandError("Too many arguments")

        return self.remove_cache_items(options, ["*"])

    def _cache_dir(self, options: Values, subdir: str) -> str:
        return os.path.join(options.cache_dir, subdir)

    def _find_http_files(self, options: Values) -> list[str]:
        old_http_dir = self._cache_dir(options, "http")
        new_http_dir = self._cache_dir(options, "http-v2")
        return filesystem.find_files(old_http_dir, "*") + filesystem.find_files(
            new_http_dir, "*"
        )

    def _find_wheels(self, options: Values, pattern: str) -> list[str]:
        wheel_dir = self._cache_dir(options, "wheels")

        # The wheel filename format, as specified in PEP 427, is:
        #     {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        #
        # Additionally, non-alphanumeric values in the distribution are
        # normalized to underscores (_), meaning hyphens can never occur
        # before `-{version}`.
        #
        # Given that information:
        # - If the pattern we're given contains a hyphen (-), the user is
        #   providing at least the version. Thus, we can just append `*.whl`
        #   to match the rest of it.
        # - If the pattern we're given doesn't contain a hyphen (-), the
        #   user is only providing the name. Thus, we append `-*.whl` to
        #   match the hyphen before the version, followed by anything else.
        #
        # PEP 427: https://www.python.org/dev/peps/pep-0427/
        pattern = pattern + ("*.whl" if "-" in pattern else "-*.whl")

        return filesystem.find_files(wheel_dir, pattern)

    def _get_http_cached_packages(
        self, options: Values, pattern: str = "*"
    ) -> list[tuple[str, str, str]]:
        """Extract package information from HTTP cached responses.

        We import Serializer and Request lazily to avoid pulling in
        network-related modules when users just invoke `pip cache --help`.
        This is required to keep test_no_network_imports passing.

        Returns a list of tuples: (package_name, version, file_path)
        """
        from pip._vendor.cachecontrol.serialize import Serializer
        from pip._vendor.requests import Request

        packages: list[tuple[str, str, str]] = []
        http_files = self._find_http_files(options)
        serializer = Serializer()

        for file_path in http_files:
            # Skip body files
            if file_path.endswith(".body"):
                continue

            try:
                with open(file_path, "rb") as f:
                    data = f.read()

                # Dummy PreparedRequest needed by Serializer API; no network call.
                dummy_request = Request("GET", "https://dummy.com").prepare()
                body_file_path = file_path + ".body"
                body_file = None

                if os.path.exists(body_file_path):
                    body_file = open(body_file_path, "rb")

                try:
                    response = serializer.loads(dummy_request, data, body_file)
                    if not response:
                        continue
                        # Check for PyPI headers that indicate this is a wheel
                    package_type = response.headers.get("x-pypi-file-package-type")
                    if package_type != "bdist_wheel":
                        continue
                    project = response.headers.get("x-pypi-file-project")
                    version = response.headers.get("x-pypi-file-version")
                    python_version = response.headers.get(
                        "x-pypi-file-python-version", "py3"
                    )
                    if not (project and version):
                        continue
                    # Create a wheel-like filename for consistency
                    wheel_name = f"{project}-{version}-{python_version}-none-any.whl"
                    # Apply pattern matching similar to wheel files
                    if pattern == "*" or self._matches_pattern(wheel_name, pattern):
                        packages.append((project, version, file_path))
                finally:
                    if body_file:
                        body_file.close()

            except Exception:
                # Silently skip files that can't be processed
                continue

        return packages

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches the given pattern."""
        import fnmatch

        # Extract just the package name-version part for matching
        base_name = filename.split("-")[0] if "-" in filename else filename

        # If pattern contains hyphen, match against full filename
        if "-" in pattern:
            return fnmatch.fnmatch(filename, pattern + "*")
        else:
            # Otherwise match against package name only
            return fnmatch.fnmatch(base_name, pattern)
