import logging
from optparse import Values
from typing import Generator, Iterable, Iterator, List, NamedTuple, Optional

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.rich import print_json

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.metadata import BaseDistribution, get_default_environment
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The output is in RFC-compliant mail header format.
    """

    usage = """
      %prog [options] <package> ..."""
    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-f",
            "--files",
            dest="files",
            action="store_true",
            default=False,
            help="Show the full list of installed files for each package.",
        )
        self.cmd_opts.add_option(
            "--format",
            dest="format",
            default="text",
            choices=("text", "json"),
            help="Select the output format among: text (default), or json",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        if not args:
            logger.warning("ERROR: Please provide a package name or names.")
            return ERROR
        query = args

        if options.format == "json":
            results = search_packages_info(query, True)
            if not print_results_json(
                results, list_files=options.files, verbose=options.verbose
            ):
                return ERROR
        else:
            results = search_packages_info(query, False)
            if not print_results(
                results, list_files=options.files, verbose=options.verbose
            ):
                return ERROR
        return SUCCESS


class _PackageInfo(NamedTuple):
    name: str
    version: str
    location: str
    requires: List[str]
    required_by: List[str]
    installer: str
    metadata_version: str
    classifiers: List[str]
    summary: str
    homepage: str
    project_urls: List[str]
    author: str
    author_email: str
    license: str
    entry_points: List[str]
    files: Optional[List[str]]


def search_packages_info(query: List[str], no_warning: bool) -> Generator[_PackageInfo, None, None]:
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    env = get_default_environment()

    installed = {dist.canonical_name: dist for dist in env.iter_all_distributions()}
    query_names = [canonicalize_name(name) for name in query]
    missing = sorted(
        [name for name, pkg in zip(query, query_names) if pkg not in installed]
    )
    if missing:
        if not no_warning:
            logger.warning("Package(s) not found: %s", ", ".join(missing))

    def _get_requiring_packages(current_dist: BaseDistribution) -> Iterator[str]:
        return (
            dist.metadata["Name"] or "UNKNOWN"
            for dist in installed.values()
            if current_dist.canonical_name
            in {canonicalize_name(d.name) for d in dist.iter_dependencies()}
        )

    for query_name in query_names:
        try:
            dist = installed[query_name]
        except KeyError:
            continue

        requires = sorted((req.name for req in dist.iter_dependencies()), key=str.lower)
        required_by = sorted(_get_requiring_packages(dist), key=str.lower)

        try:
            entry_points_text = dist.read_text("entry_points.txt")
            entry_points = entry_points_text.splitlines(keepends=False)
        except FileNotFoundError:
            entry_points = []

        files_iter = dist.iter_declared_entries()
        if files_iter is None:
            files: Optional[List[str]] = None
        else:
            files = sorted(files_iter)

        metadata = dist.metadata

        yield _PackageInfo(
            name=dist.raw_name,
            version=str(dist.version),
            location=dist.location or "",
            requires=requires,
            required_by=required_by,
            installer=dist.installer,
            metadata_version=dist.metadata_version or "",
            classifiers=metadata.get_all("Classifier", []),
            summary=metadata.get("Summary", ""),
            homepage=metadata.get("Home-page", ""),
            project_urls=metadata.get_all("Project-URL", []),
            author=metadata.get("Author", ""),
            author_email=metadata.get("Author-email", ""),
            license=metadata.get("License", ""),
            entry_points=entry_points,
            files=files,
        )


def print_results(
    distributions: Iterable[_PackageInfo],
    list_files: bool,
    verbose: bool,
) -> bool:
    """
    Print the information from installed distributions found.
    """
    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            write_output("---")

        write_output("Name: %s", dist.name)
        write_output("Version: %s", dist.version)
        write_output("Summary: %s", dist.summary)
        write_output("Home-page: %s", dist.homepage)
        write_output("Author: %s", dist.author)
        write_output("Author-email: %s", dist.author_email)
        write_output("License: %s", dist.license)
        write_output("Location: %s", dist.location)
        write_output("Requires: %s", ", ".join(dist.requires))
        write_output("Required-by: %s", ", ".join(dist.required_by))

        if verbose:
            write_output("Metadata-Version: %s", dist.metadata_version)
            write_output("Installer: %s", dist.installer)
            write_output("Classifiers:")
            for classifier in dist.classifiers:
                write_output("  %s", classifier)
            write_output("Entry-points:")
            for entry in dist.entry_points:
                write_output("  %s", entry.strip())
            write_output("Project-URLs:")
            for project_url in dist.project_urls:
                write_output("  %s", project_url)
        if list_files:
            write_output("Files:")
            if dist.files is None:
                write_output("Cannot locate RECORD or installed-files.txt")
            else:
                for line in dist.files:
                    write_output("  %s", line.strip())
    return results_printed


def print_results_json(
    distributions: Iterable[_PackageInfo],
    list_files: bool,
    verbose: bool,
) -> bool:
    """
    Print the information from installed distributions found in JSON format.
    """
    output = []
    for dist in distributions:
        package_dict = {}

        package_dict["Name"] = dist.name
        package_dict["Version"] = dist.version
        package_dict["Summary"] = dist.summary
        package_dict["Home-Page"] = dist.homepage
        package_dict["Author"] = dist.author
        package_dict["Author-email"] = dist.author_email
        package_dict["License"] = dist.license
        package_dict["Location"] = dist.location
        package_dict["Requires"] = dist.requires
        package_dict["Required-by"] = dist.required_by

        if verbose:
            package_dict["Metadata-Version"] = dist.metadata_version
            package_dict["Installer"] = dist.installer
            package_dict["Classifiers"] = []
            for classifier in dist.classifiers:
                package_dict["Classifiers"].append(classifier)
            package_dict["Entry-points"] = []
            for entry in dist.entry_points:
                package_dict["Entry-points"].append(entry.strip())
            package_dict["Project-URLs"] = {}
            for project_url in dist.project_urls:
                name, url = project_url.split(", ", 1)
                package_dict["Project-URLs"][name] = url
        if list_files:
            package_dict["Files"] = []
            if dist.files is not None:
                for line in dist.files:
                    package_dict["Files"].append(line.strip())

        output.append(package_dict)

    print_json(data=output)

    return len(output) > 0
