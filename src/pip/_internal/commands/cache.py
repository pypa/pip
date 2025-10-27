from __future__ import annotations

import os
import textwrap
from optparse import Values
from typing import Callable

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import filesystem
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import format_size

logger = getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's wheel cache.

    Subcommands:

    - dir: Show the cache directory.
    - info: Show information about the cache.
    - list: List filenames of stored cache (wheels and HTTP cached packages).
    - remove: Remove one or more package from the cache.
    - purge: Remove all items from the cache.

    ``<pattern>`` can be a glob expression or a package name.
    """

    ignore_require_venv = True
    usage = """
        %prog dir
        %prog info
        %prog list [<pattern>] [--format=[human, abspath]] [--http] [--all]
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
            "--http",
            action="store_true",
            dest="list_http",
            default=False,
            help="List HTTP cached package files",
        )

        self.cmd_opts.add_option(
            "--all",
            action="store_true",
            dest="list_all",
            default=False,
            help="List both HTTP cached and locally built package files",
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

        if args:
            pattern = args[0]
        else:
            pattern = "*"

        # Determine what to show based on flags
        # Default: show only wheels (backward compatible)
        # --http: show only HTTP cache
        # --all: show both wheels and HTTP cache (unified)
        if options.list_all:
            show_wheels = True
            show_http = True
            unified = True
        elif options.list_http:
            show_wheels = False
            show_http = True
            unified = False
        else:
            # Default behavior
            show_wheels = True
            show_http = False
            unified = False

        wheel_files = []
        if show_wheels:
            wheel_files = self._find_wheels(options, pattern)

        http_files = []
        if show_http:
            http_files = self._get_http_cache_files_with_metadata(options)

        if options.list_format == "human":
            if unified:
                self.format_for_human_unified_all(wheel_files, http_files)
            else:
                self.format_for_human_separated(
                    wheel_files, http_files, show_http, show_wheels
                )
        else:
            self.format_for_abspath_unified(wheel_files, http_files)

    def format_for_human_separated(
        self,
        wheel_files: list[str],
        http_files: list[tuple[str, str]],
        show_http: bool,
        show_wheels: bool,
    ) -> None:
        """Format wheel and HTTP cache files in separate sections."""
        if not wheel_files and not http_files:
            if show_http:
                logger.info("No cached files.")
            else:
                logger.info("No locally built wheels cached.")
            return

        # When showing HTTP files only, use a separate section
        if show_http and http_files:
            logger.info("HTTP cache files:")
            formatted = []
            for cache_file, filename in http_files:
                # Use body file size if available
                body_file = cache_file + ".body"
                if os.path.exists(body_file):
                    size = filesystem.format_file_size(body_file)
                else:
                    size = filesystem.format_file_size(cache_file)

                # Only show files where we extracted a filename
                # (filename should always be present since we filter in
                # _get_http_cache_files_with_metadata)
                formatted.append(f" - {filename} ({size})")

            logger.info("\n".join(sorted(formatted)))

        # When showing wheels, list them
        if show_wheels and wheel_files:
            if show_http and http_files:
                logger.info("")  # Add spacing between sections
            formatted = []
            for filename in wheel_files:
                wheel = os.path.basename(filename)
                size = filesystem.format_file_size(filename)
                formatted.append(f" - {wheel} ({size})")

            logger.info("\n".join(sorted(formatted)))

    def format_for_human_unified_all(
        self,
        wheel_files: list[str],
        http_files: list[tuple[str, str]],
    ) -> None:
        """Format wheel and HTTP cache files in a unified list with
        [HTTP cached] suffix.
        """
        if not wheel_files and not http_files:
            logger.info("No cached files.")
            return

        formatted = []

        # Add HTTP files with suffix
        for cache_file, filename in http_files:
            # Use body file size if available
            body_file = cache_file + ".body"
            if os.path.exists(body_file):
                size = filesystem.format_file_size(body_file)
            else:
                size = filesystem.format_file_size(cache_file)

            formatted.append(f" - {filename} ({size}) [HTTP cached]")

        # Add wheel files without suffix
        for filename in wheel_files:
            wheel = os.path.basename(filename)
            size = filesystem.format_file_size(filename)
            formatted.append(f" - {wheel} ({size})")

        logger.info("\n".join(sorted(formatted)))

    def format_for_abspath_unified(
        self, wheel_files: list[str], http_files: list[tuple[str, str]]
    ) -> None:
        """Format wheel and HTTP cache files as absolute paths."""
        all_files = []

        # Add wheel files
        all_files.extend(wheel_files)

        # Add HTTP cache files (only those with extracted filenames)
        for cache_file, _filename in http_files:
            all_files.append(cache_file)

        if all_files:
            logger.info("\n".join(sorted(all_files)))

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

    def _get_http_cache_files_with_metadata(
        self, options: Values
    ) -> list[tuple[str, str]]:
        """Get HTTP cache files with filenames from package content inspection.

        Extracts filenames by reading the cached package structure:
        - Wheel files: Reads .dist-info/WHEEL metadata for complete filename with tags
        - Tarball files: Reads tar structure to extract package name from root directory

        Returns a list of tuples: (cache_file_path, filename)
        Only returns files where a filename could be successfully extracted.
        """
        from pip._vendor.cachecontrol.serialize import Serializer

        http_files = self._find_http_files(options)
        result = []

        serializer = Serializer()

        for cache_file in http_files:
            # Skip .body files as we only want metadata files
            if cache_file.endswith(".body"):
                continue

            filename = None
            try:
                # Read the cached metadata
                with open(cache_file, "rb") as f:
                    cached_data = f.read()

                # Try to parse it
                if cached_data.startswith(f"cc={serializer.serde_version},".encode()):
                    # Extract the msgpack data
                    from pip._vendor import msgpack

                    data = cached_data[5:]  # Skip "cc=4,"
                    cached = msgpack.loads(data, raw=False)

                    headers = cached.get("response", {}).get("headers", {})
                    content_type = headers.get("content-type", "")

                    # Extract filename from body content
                    body_file = cache_file + ".body"
                    if os.path.exists(body_file):
                        filename = self._extract_filename_from_body(
                            body_file, content_type
                        )
            except Exception:
                # If we can't read/parse the file, just skip trying to extract name
                pass

            # Only include files where we successfully extracted a filename
            if filename:
                result.append((cache_file, filename))

        return result

    def _extract_filename_from_body(
        self, body_file: str, content_type: str
    ) -> str | None:
        """Extract filename by inspecting the body content.

        This works offline by examining the downloaded file structure.
        """
        try:
            # Check if it's a wheel file (ZIP format)
            if "application/octet-stream" in content_type or not content_type:
                # Try to read as a wheel (ZIP file)
                import zipfile

                try:
                    with zipfile.ZipFile(body_file, "r") as zf:
                        # Wheel files contain a .dist-info directory
                        names = zf.namelist()
                        dist_info_dir = None
                        for name in names:
                            if ".dist-info/" in name:
                                dist_info_dir = name.split("/")[0]
                                break

                        if dist_info_dir and dist_info_dir.endswith(".dist-info"):
                            # Read WHEEL metadata to get the full wheel name
                            wheel_file = f"{dist_info_dir}/WHEEL"
                            if wheel_file in names:
                                wheel_content = zf.read(wheel_file).decode("utf-8")
                                # Parse WHEEL file for Root-Is-Purelib and Tag
                                tags = []
                                for line in wheel_content.split("\n"):
                                    if line.startswith("Tag:"):
                                        tag = line.split(":", 1)[1].strip()
                                        tags.append(tag)

                                if tags:
                                    # Use first tag to construct filename
                                    # Format: {name}-{version}.dist-info
                                    pkg_info = dist_info_dir[: -len(".dist-info")]
                                    # Tags format: py3-none-any
                                    tag = tags[0]
                                    return f"{pkg_info}-{tag}.whl"

                            # Fallback: just use name-version.whl
                            pkg_info = dist_info_dir[: -len(".dist-info")]
                            return f"{pkg_info}.whl"
                except (zipfile.BadZipFile, KeyError, UnicodeDecodeError):
                    pass

                # Try to read as a tarball
                import tarfile

                try:
                    with tarfile.open(body_file, "r:*") as tf:
                        # Get the first member to determine the package name
                        members = tf.getmembers()
                        if members:
                            # Tarball usually has format: package-version/...
                            first_name = members[0].name
                            pkg_dir = first_name.split("/")[0]
                            if pkg_dir and "-" in pkg_dir:
                                return f"{pkg_dir}.tar.gz"
                except (tarfile.TarError, KeyError):
                    pass

        except Exception:
            pass

        return None
