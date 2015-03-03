import logging
import warnings

from pip.exceptions import DistributionNotFound
from pip.index import PackageFinder
from pip.req import InstallRequirement
from pip.utils import get_installed_distributions
from pip.utils.deprecation import RemovedInPip7Warning


logger = logging.getLogger(__name__)


def find_packages_latests_versions(options, build_session_func):
    index_urls = [options.index_url] + options.extra_index_urls
    if options.no_index:
        logger.info('Ignoring indexes: %s', ','.join(index_urls))
        index_urls = []

    if options.use_mirrors:
        warnings.warn(
            "--use-mirrors has been deprecated and will be removed in the "
            "future. Explicit uses of --index-url and/or --extra-index-url"
            " is suggested.",
            RemovedInPip7Warning,
        )

    if options.mirrors:
        warnings.warn(
            "--mirrors has been deprecated and will be removed in the "
            "future. Explicit uses of --index-url and/or --extra-index-url"
            " is suggested.",
            RemovedInPip7Warning,
        )
        index_urls += options.mirrors

    dependency_links = []
    for dist in get_installed_distributions(local_only=options.local,
                                            user_only=options.user):
        if dist.has_metadata('dependency_links.txt'):
            dependency_links.extend(
                dist.get_metadata_lines('dependency_links.txt'),
            )

    with build_session_func(options) as session:
        finder = _build_package_finder(options, index_urls, session)
        finder.add_dependency_links(dependency_links)

        installed_packages = get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
            include_editables=False,
        )
        for dist in installed_packages:
            req = InstallRequirement.from_line(
                dist.key, None, isolated=options.isolated_mode,
            )
            try:
                link = finder.find_requirement(req, True)

                # If link is None, means installed version is most
                # up-to-date
                if link is None:
                    continue
            except DistributionNotFound:
                continue
            else:
                remote_version = finder._link_package_versions(
                    link, req.name
                ).version
            yield dist, remote_version


def _build_package_finder(options, index_urls, session):
    """
    Create a package finder appropriate to this list command.
    """
    return PackageFinder(
        find_links=options.find_links,
        index_urls=index_urls,
        allow_external=options.allow_external,
        allow_unverified=options.allow_unverified,
        allow_all_external=options.allow_all_external,
        allow_all_prereleases=options.pre,
        trusted_hosts=options.trusted_hosts,
        process_dependency_links=options.process_dependency_links,
        session=session,
    )
