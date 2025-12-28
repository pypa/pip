import logging
import os
from optparse import Values
from pathlib import Path
from zipfile import ZipFile

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.metadata import get_metadata_distribution
from pip._internal.network.download import Downloader
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.operations.prepare import get_http_url
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

        downloaded: list[str] = []

        if options.metadata_only:
            # For metadata-only mode, fetch metadata directly without
            # downloading full packages
            for req in requirement_set.requirements.values():
                if req.satisfied_by is None:
                    assert req.name is not None
                    self._download_metadata_only(
                        req, options.download_dir, session, finder
                    )
                    downloaded.append(req.name)
        else:
            # Normal download mode - download full packages
            preparer.prepare_linked_requirements_more(
                requirement_set.requirements.values()
            )
            for req in requirement_set.requirements.values():
                if req.satisfied_by is None:
                    assert req.name is not None
                    preparer.save_linked_requirement(req)
                    downloaded.append(req.name)

        if downloaded:
            action = "metadata for" if options.metadata_only else "downloaded"
            write_output("Successfully %s %s", action, " ".join(downloaded))

        return SUCCESS

    def _download_metadata_only(self, req, download_dir: str, session, finder) -> None:
        """Fetch and save only metadata from a package without downloading the
        full package.

        Tries multiple approaches in order:
        1. PEP 658: Fetch metadata directly from .metadata URL (fast, no wheel download)
        2. Fallback: Download full wheel and extract metadata

        This significantly reduces bandwidth usage for metadata-only operations.
        """
        assert req.link is not None, "Requirement must have a link"
        output_dir = Path(download_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try PEP 658 metadata first (fastest - no package download)
        metadata_link = req.link.metadata_link()
        if metadata_link:
            logger.info("Fetching metadata for %s via PEP 658", req.name)
            try:
                self._fetch_pep658_metadata(req, metadata_link, output_dir, session)
                return
            except Exception as e:
                logger.warning(
                    "Failed to fetch PEP 658 metadata for %s: %s", req.name, e
                )

        # For wheels without PEP 658: download wheel and extract metadata
        if req.link.is_wheel:
            logger.info("Downloading wheel to extract metadata for %s", req.name)
            self._extract_metadata_from_wheel(req, output_dir, session)
        else:
            logger.warning(
                "Metadata-only download not supported for source distribution: %s. "
                "PEP 658 metadata not available. "
                "Consider using --only-binary=:all: to restrict to wheels.",
                req.name,
            )

    def _fetch_pep658_metadata(self, req, metadata_link, output_dir: Path, session):
        """Fetch metadata using PEP 658 (separate .metadata file)."""
        # Create a downloader instance
        downloader = Downloader(session, progress_bar="on")

        # Download the metadata file
        metadata_file = get_http_url(
            metadata_link,
            downloader,
            hashes=metadata_link.as_hashes(),
        )

        # Read metadata content
        with open(metadata_file.path, "rb") as f:
            metadata_contents = f.read()

        # Create a metadata distribution object
        metadata_dist = get_metadata_distribution(
            metadata_contents,
            req.link.filename,
            canonicalize_name(req.name),
        )

        # Save metadata to .dist-info directory
        dist_info_name = f"{metadata_dist.raw_name}-{metadata_dist.version}.dist-info"
        dist_info_path = output_dir / dist_info_name
        dist_info_path.mkdir(parents=True, exist_ok=True)

        # Write METADATA file
        metadata_path = dist_info_path / "METADATA"
        metadata_path.write_bytes(metadata_contents)

        logger.info("Saved metadata to %s", dist_info_path)

    def _extract_metadata_from_wheel(self, req, output_dir: Path, session):
        """Download wheel and extract only .dist-info directory."""
        # Create a downloader instance
        downloader = Downloader(session, progress_bar="on")

        # Download the wheel file to a temporary location
        temp_dir = TempDirectory(kind="metadata-extract", globally_managed=True)
        wheel_file = get_http_url(
            req.link,
            downloader,
            download_dir=temp_dir.path,
        )

        wheel_path = Path(wheel_file.path)

        # Extract metadata from the wheel
        try:
            with ZipFile(wheel_path, "r") as wheel_zip:
                # Find the .dist-info directory
                dist_info_dir = wheel_dist_info_dir(wheel_zip, req.name)

                # Extract only files from .dist-info directory
                dist_info_members = [
                    name
                    for name in wheel_zip.namelist()
                    if name.startswith(f"{dist_info_dir}/")
                ]

                # Extract metadata files
                for member in dist_info_members:
                    target_path = output_dir / member
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract file content
                    with wheel_zip.open(member) as source:
                        target_path.write_bytes(source.read())

                logger.info("Extracted metadata for %s to %s", req.name, output_dir)

        except Exception as e:
            logger.error("Failed to extract metadata from %s: %s", wheel_path, e)
            raise
