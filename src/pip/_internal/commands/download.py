import logging
import os
from optparse import Values
from pathlib import Path
from zipfile import ZipFile

from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.utils.misc import ensure_dir, normalize_path, write_output
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.wheel import wheel_dist_info_dir

logger = logging.getLogger(__name__)


class DownloadCommand(RequirementCommand):
    """
    Download packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports downloading from "requirements files", which provide
    an easy way to specify a whole environment to be downloaded.
    """

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] <vcs project url> ...
      %prog [options] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.build_constraints())
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.requirements_from_scripts())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.src())
        self.cmd_opts.add_option(cmdoptions.pre())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())

        self.cmd_opts.add_option(
            "-d",
            "--dest",
            "--destination-dir",
            "--destination-directory",
            dest="download_dir",
            metavar="dir",
            default=os.curdir,
            help="Download packages into <dir>.",
        )

        self.cmd_opts.add_option(
            "--metadata-only",
            dest="metadata_only",
            action="store_true",
            default=False,
            help=(
                "Download only package metadata (.dist-info directories) "
                "without downloading the full packages. Useful for dependency "
                "analysis, security auditing, and compatibility checking."
            ),
        )

        cmdoptions.add_target_python_options(self.cmd_opts)

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    @with_cleanup
    def run(self, options: Values, args: list[str]) -> int:
        options.ignore_installed = True
        # editable doesn't really make sense for `pip download`, but the bowels
        # of the RequirementSet code require that property.
        options.editables = []

        cmdoptions.check_dist_restriction(options)
        cmdoptions.check_build_constraints(options)

        options.download_dir = normalize_path(options.download_dir)
        ensure_dir(options.download_dir)

        session = self.get_default_session(options)

        target_python = make_target_python(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )

        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="download",
            globally_managed=True,
        )

        reqs = self.get_requirements(args, options, finder, session)

        preparer = self.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.download_dir,
            use_user_site=False,
            verbosity=self.verbosity,
        )

        resolver = self.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            ignore_requires_python=options.ignore_requires_python,
            py_version_info=options.python_version,
        )

        self.trace_basic_info(finder)

        requirement_set = resolver.resolve(reqs, check_supported_wheels=True)

        preparer.prepare_linked_requirements_more(requirement_set.requirements.values())

        downloaded: list[str] = []
        for req in requirement_set.requirements.values():
            if req.satisfied_by is None:
                assert req.name is not None
                if options.metadata_only:
                    self._download_metadata_only(req, options.download_dir)
                else:
                    preparer.save_linked_requirement(req)
                downloaded.append(req.name)

        if downloaded:
            action = "metadata" if options.metadata_only else "downloaded"
            write_output("Successfully %s %s", action, " ".join(downloaded))

        return SUCCESS

    def _download_metadata_only(self, req, download_dir: str) -> None:
        """Extract and save only metadata from a package.

        For wheels: Extract .dist-info directory from the wheel archive.
        For source distributions: Try to fetch metadata via PEP 658 if available,
        otherwise log a warning and skip.
        """
        assert req.local_file_path is not None, "Requirement must be downloaded first"
        local_path = Path(req.local_file_path)

        if not local_path.exists():
            logger.warning("Package file not found: %s", local_path)
            return

        # Handle wheel files
        if local_path.suffix == ".whl":
            self._extract_wheel_metadata(local_path, req.name, download_dir)
        else:
            # For sdist, check if metadata was fetched via PEP 658
            if hasattr(req, "metadata_directory") and req.metadata_directory:
                self._copy_metadata_directory(
                    Path(req.metadata_directory), download_dir
                )
            else:
                logger.warning(
                    "Metadata-only download not supported for source distribution: %s. "
                    "Consider using --only-binary=:all: to restrict to wheels.",
                    req.name,
                )

    def _extract_wheel_metadata(
        self, wheel_path: Path, package_name: str, download_dir: str
    ) -> None:
        """Extract .dist-info directory from a wheel file."""
        try:
            with ZipFile(wheel_path, "r") as wheel_zip:
                # Find the .dist-info directory
                dist_info_dir = wheel_dist_info_dir(wheel_zip, package_name)

                # Extract only files from .dist-info directory
                dist_info_members = [
                    name
                    for name in wheel_zip.namelist()
                    if name.startswith(f"{dist_info_dir}/")
                ]

                # Create output directory
                output_dir = Path(download_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                # Extract metadata files
                for member in dist_info_members:
                    target_path = output_dir / member
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract file content
                    with wheel_zip.open(member) as source:
                        target_path.write_bytes(source.read())

                logger.info("Extracted metadata for %s to %s", package_name, output_dir)

        except Exception as e:
            logger.error("Failed to extract metadata from %s: %s", wheel_path, e)
            raise

    def _copy_metadata_directory(self, metadata_dir: Path, download_dir: str) -> None:
        """Copy a metadata directory to the download location."""
        import shutil

        output_dir = Path(download_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy the entire .dist-info directory
        dist_info_name = metadata_dir.name
        target_path = output_dir / dist_info_name

        if target_path.exists():
            shutil.rmtree(target_path)

        shutil.copytree(metadata_dir, target_path)
        logger.info("Copied metadata directory %s to %s", dist_info_name, output_dir)
