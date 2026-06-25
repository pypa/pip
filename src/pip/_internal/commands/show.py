from __future__ import annotations

import logging
import string
from collections.abc import Generator, Iterable
from optparse import Values
from typing import NamedTuple

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.metadata import (
    BaseDistribution,
    BaseEnvironment,
    get_default_environment,
    select_backend,
)
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


def normalize_project_url_label(label: str) -> str:
    # This logic is from PEP 753 (Well-known Project URLs in Metadata).
    chars_to_remove = string.punctuation + string.whitespace
    removal_map = str.maketrans("", "", chars_to_remove)
    return label.translate(removal_map).lower()


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

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: list[str]) -> int:
        if not args:
            logger.warning("ERROR: Please provide a package name or names.")
            return ERROR
        query = args

        results = search_packages_info(query)
        if not print_results(
            results, list_files=options.files, verbose=options.verbose
        ):
            return ERROR
        return SUCCESS


class _PackageInfo(NamedTuple):
    name: str
    version: str
    location: str
    editable_project_location: str | None
    requires: list[str]
    required_by: list[str]
    installer: str
    metadata_version: str
    classifiers: list[str]
    summary: str
    homepage: str
    project_urls: list[str]
    author: str
    author_email: str
    license: str
    license_expression: str
    entry_points: list[str]
    files: list[str] | None


def _canonicalize_name_cached(
    name: str,
    canonical_names: dict[str, NormalizedName],
) -> NormalizedName:
    try:
        return canonical_names[name]
    except KeyError:
        canonical_name = canonicalize_name(name)
        canonical_names[name] = canonical_name
        return canonical_name


def _get_requiring_packages(
    current_dist: BaseDistribution,
    distributions: list[BaseDistribution],
    canonical_names: dict[str, NormalizedName],
) -> list[str]:
    current_name = current_dist.canonical_name
    canonical_names_get = canonical_names.get
    required_by: list[str] = []
    add_required_by = required_by.append

    for dist in distributions:
        for dependency in dist.iter_dependencies():
            dependency_name = dependency.name
            if dependency_name == current_name:
                add_required_by(dist.metadata["Name"] or "UNKNOWN")
                break

            canonical_name = canonical_names_get(dependency_name)
            if canonical_name is None:
                canonical_name = canonicalize_name(dependency_name)
                canonical_names[dependency_name] = canonical_name

            if canonical_name == current_name:
                add_required_by(dist.metadata["Name"] or "UNKNOWN")
                break

    required_by.sort(key=str.lower)
    return required_by


def _get_single_package_info(
    env: BaseEnvironment,
    query_name: NormalizedName,
) -> tuple[dict[NormalizedName, BaseDistribution], list[BaseDistribution]]:
    installed: dict[NormalizedName, BaseDistribution] = {}
    distributions = list(env.iter_all_distributions())
    for dist in distributions:
        if dist.canonical_name == query_name:
            installed[query_name] = dist
    return installed, distributions


def _get_multi_package_info(
    env: BaseEnvironment,
    query_names_set: set[NormalizedName],
    canonical_names: dict[str, NormalizedName],
) -> tuple[
    dict[NormalizedName, BaseDistribution],
    dict[NormalizedName, list[str]],
    set[NormalizedName],
    dict[NormalizedName, list[str]],
    bool,
]:
    installed: dict[NormalizedName, BaseDistribution] = {}
    has_required_by_error = False
    dist_requires: dict[NormalizedName, list[str]] = {}
    dist_requires_with_error: set[NormalizedName] = set()
    required_by_inputs: dict[NormalizedName, set[str]] = {}

    for dist in env.iter_all_distributions():
        is_query_dist = dist.canonical_name in query_names_set
        if is_query_dist:
            installed[dist.canonical_name] = dist
        try:
            requires_set: set[str] | None = set() if is_query_dist else None
            for dependency in dist.iter_dependencies():
                dependency_name = dependency.name
                canonical_name = _canonicalize_name_cached(
                    dependency_name,
                    canonical_names,
                )

                if requires_set is not None:
                    requires_set.add(dependency_name)

                if canonical_name in query_names_set:
                    required_by_inputs.setdefault(canonical_name, set()).add(
                        dist.metadata["Name"] or "UNKNOWN"
                    )

            if is_query_dist:
                # Avoid duplicates in requirements, e.g. due to environment markers.
                dist_requires[dist.canonical_name] = sorted(
                    requires_set or (),
                    key=str.lower,
                )
        except InvalidRequirement:
            if is_query_dist:
                dist_requires_with_error.add(dist.canonical_name)
                if select_backend().NAME == "importlib":
                    has_required_by_error = True
            else:
                has_required_by_error = True
            continue

    required_by_map = {
        package: sorted(requirements, key=str.lower)
        for package, requirements in required_by_inputs.items()
    }
    return (
        installed,
        dist_requires,
        dist_requires_with_error,
        required_by_map,
        has_required_by_error,
    )


def search_packages_info(query: list[str]) -> Generator[_PackageInfo, None, None]:
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    env = get_default_environment()

    query_names = [canonicalize_name(name) for name in query]
    query_names_set = set(query_names)
    is_single_query = len(query_names) == 1
    canonical_names: dict[str, NormalizedName] = {}

    if is_single_query:
        query_name = query_names[0]
        installed, distributions = _get_single_package_info(env, query_name)
    else:
        (
            installed,
            dist_requires,
            dist_requires_with_error,
            required_by_map,
            has_required_by_error,
        ) = _get_multi_package_info(env, query_names_set, canonical_names)

    missing = sorted(
        [name for name, pkg in zip(query, query_names) if pkg not in installed]
    )
    if missing:
        logger.warning("Package(s) not found: %s", ", ".join(missing))

    for query_name in query_names:
        try:
            dist = installed[query_name]
        except KeyError:
            continue

        if is_single_query:
            try:
                # Avoid duplicates in requirements, e.g. due to environment markers.
                requires = sorted(
                    {req.name for req in dist.iter_dependencies()},
                    key=str.lower,
                )
            except InvalidRequirement:
                requires = sorted(dist.iter_raw_dependencies(), key=str.lower)

            try:
                required_by = _get_requiring_packages(
                    dist,
                    distributions,
                    canonical_names,
                )
            except InvalidRequirement:
                required_by = ["#N/A"]
        else:
            if dist.canonical_name in dist_requires_with_error:
                requires = sorted(dist.iter_raw_dependencies(), key=str.lower)
            else:
                requires = dist_requires.get(dist.canonical_name, [])

            if has_required_by_error:
                required_by = ["#N/A"]
            else:
                required_by = required_by_map.get(dist.canonical_name, [])

        try:
            entry_points_text = dist.read_text("entry_points.txt")
            entry_points = entry_points_text.splitlines(keepends=False)
        except FileNotFoundError:
            entry_points = []

        files_iter = dist.iter_declared_entries()
        if files_iter is None:
            files: list[str] | None = None
        else:
            files = sorted(files_iter)

        metadata = dist.metadata

        project_urls = metadata.get_all("Project-URL", [])
        homepage = metadata.get("Home-page", "")
        if not homepage:
            # It's common that there is a "homepage" Project-URL, but Home-page
            # remains unset (especially as PEP 621 doesn't surface the field).
            for url in project_urls:
                url_label, url = url.split(",", maxsplit=1)
                normalized_label = normalize_project_url_label(url_label)
                if normalized_label == "homepage":
                    homepage = url.strip()
                    break

        yield _PackageInfo(
            name=dist.raw_name,
            version=dist.raw_version,
            location=dist.location or "",
            editable_project_location=dist.editable_project_location,
            requires=requires,
            required_by=required_by,
            installer=dist.installer,
            metadata_version=dist.metadata_version or "",
            classifiers=metadata.get_all("Classifier", []),
            summary=metadata.get("Summary", ""),
            homepage=homepage,
            project_urls=project_urls,
            author=metadata.get("Author", ""),
            author_email=metadata.get("Author-email", ""),
            license=metadata.get("License", ""),
            license_expression=metadata.get("License-Expression", ""),
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

        metadata_version = dist.metadata_version
        metadata_version_tuple = (
            tuple(map(int, metadata_version.split("."))) if metadata_version else ()
        )

        write_output("Name: %s", dist.name)
        write_output("Version: %s", dist.version)
        write_output("Summary: %s", dist.summary)
        write_output("Home-page: %s", dist.homepage)
        write_output("Author: %s", dist.author)
        write_output("Author-email: %s", dist.author_email)
        if metadata_version_tuple >= (2, 4) and dist.license_expression:
            write_output("License-Expression: %s", dist.license_expression)
        else:
            write_output("License: %s", dist.license)
        write_output("Location: %s", dist.location)
        if dist.editable_project_location is not None:
            write_output(
                "Editable project location: %s", dist.editable_project_location
            )
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
