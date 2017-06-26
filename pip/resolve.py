"""Dependency Resolution

The dependency resolution in pip is performed as follows:

for top-level requirements:
    a. only one spec allowed per project, regardless of conflicts or not.
       otherwise a "double requirement" exception is raised
    b. they override sub-dependency requirements.
for sub-dependencies
    a. "first found, wins" (where the order is breadth first)
"""

import logging
import os
from itertools import chain

from pip._vendor import pkg_resources, requests

from pip.download import (
    is_dir_url, is_file_url, is_vcs_url, unpack_url, url_to_path
)
from pip.exceptions import (
    BestVersionAlreadyInstalled, DirectoryUrlHashUnsupported,
    DistributionNotFound, HashError, HashErrors, HashUnpinned,
    InstallationError, PreviousBuildDirError, UnsupportedPythonVersion,
    VcsHashUnsupported
)
from pip.req.req_install import InstallRequirement
from pip.utils import display_path, dist_in_usersite, ensure_dir
from pip.utils.hashes import MissingHashes
from pip.utils.logging import indent_log
from pip.utils.packaging import check_dist_requires_python
from pip.vcs import vcs

logger = logging.getLogger(__name__)


def make_abstract_dist(req_to_install):
    """Factory to make an abstract dist object.

    Preconditions: Either an editable req with a source_dir, or satisfied_by or
    a wheel link, or a non-editable req with a source_dir.

    :return: A concrete DistAbstraction.
    """
    if req_to_install.editable:
        return IsSDist(req_to_install)
    elif req_to_install.link and req_to_install.link.is_wheel:
        return IsWheel(req_to_install)
    else:
        return IsSDist(req_to_install)


class DistAbstraction(object):
    """Abstracts out the wheel vs non-wheel Resolver.resolve() logic.

    The requirements for anything installable are as follows:
     - we must be able to determine the requirement name
       (or we can't correctly handle the non-upgrade case).
     - we must be able to generate a list of run-time dependencies
       without installing any additional packages (or we would
       have to either burn time by doing temporary isolated installs
       or alternatively violate pips 'don't start installing unless
       all requirements are available' rule - neither of which are
       desirable).
     - for packages with setup requirements, we must also be able
       to determine their requirements without installing additional
       packages (for the same reason as run-time dependencies)
     - we must be able to create a Distribution object exposing the
       above metadata.
    """

    def __init__(self, req_to_install):
        self.req_to_install = req_to_install

    def dist(self, finder):
        """Return a setuptools Dist object."""
        raise NotImplementedError(self.dist)

    def prep_for_dist(self):
        """Ensure that we can get a Dist for this requirement."""
        raise NotImplementedError(self.dist)


class IsWheel(DistAbstraction):

    def dist(self, finder):
        return list(pkg_resources.find_distributions(
            self.req_to_install.source_dir))[0]

    def prep_for_dist(self):
        # FIXME:https://github.com/pypa/pip/issues/1112
        pass


class IsSDist(DistAbstraction):

    def dist(self, finder):
        dist = self.req_to_install.get_dist()
        # FIXME: shouldn't be globally added:
        if dist.has_metadata('dependency_links.txt'):
            finder.add_dependency_links(
                dist.get_metadata_lines('dependency_links.txt')
            )
        return dist

    def prep_for_dist(self):
        self.req_to_install.run_egg_info()
        self.req_to_install.assert_source_matches_version()


class Installed(DistAbstraction):

    def dist(self, finder):
        return self.req_to_install.satisfied_by

    def prep_for_dist(self):
        pass


class Resolver(object):
    """Resolves which packages need to be installed/uninstalled to perform \
    the requested operation without breaking the requirements of any package.
    """

    def __init__(self, upgrade_strategy, finder):
        super(Resolver, self).__init__()
        assert upgrade_strategy in ["eager", "only-if-needed", "not-allowed"]
        self.upgrade_strategy = upgrade_strategy
        self.finder = finder

    def resolve(self, requirement_set):
        """Resolve what operations need to be done

        As a side-effect of this method, the packages (and their dependencies)
        are downloaded, unpacked and prepared for installation.

        Once PyPI has static dependency metadata available, it would be
        possible to move this side-effect to become a step separated from
        dependency resolution.
        """
        # make the wheelhouse
        if requirement_set.wheel_download_dir:
            ensure_dir(requirement_set.wheel_download_dir)

        # If any top-level requirement has a hash specified, enter
        # hash-checking mode, which requires hashes from all.
        root_reqs = (
            requirement_set.unnamed_requirements +
            requirement_set.requirements.values()
        )
        require_hashes = (
            requirement_set.require_hashes or
            any(req.has_hash_options for req in root_reqs)
        )

        # Display where finder is looking for packages
        locations = self.finder.get_formatted_locations()
        if locations:
            logger.info(locations)

        # Actually prepare the files, and collect any exceptions. Most hash
        # exceptions cannot be checked ahead of time, because
        # req.populate_link() needs to be called before we can make decisions
        # based on link type.
        discovered_reqs = []
        hash_errors = HashErrors()
        for req in chain(root_reqs, discovered_reqs):
            try:
                discovered_reqs.extend(self._resolve_one(
                    requirement_set,
                    req,
                    require_hashes=require_hashes,
                    ignore_dependencies=requirement_set.ignore_dependencies))
            except HashError as exc:
                exc.req = req
                hash_errors.append(exc)

        if hash_errors:
            raise hash_errors

    def _is_upgrade_allowed(self, req):
        if self.upgrade_strategy == "not-allowed":
            return False
        elif self.upgrade_strategy == "eager":
            return True
        else:
            assert self.upgrade_strategy == "only-if-needed"
            return req.is_direct

    # XXX: Stop passing requirement_set for options
    def _check_skip_installed(self, req_to_install, requirement_set):
        """Check if req_to_install should be skipped.

        This will check if the req is installed, and whether we should upgrade
        or reinstall it, taking into account all the relevant user options.

        After calling this req_to_install will only have satisfied_by set to
        None if the req_to_install is to be upgraded/reinstalled etc. Any
        other value will be a dist recording the current thing installed that
        satisfies the requirement.

        Note that for vcs urls and the like we can't assess skipping in this
        routine - we simply identify that we need to pull the thing down,
        then later on it is pulled down and introspected to assess upgrade/
        reinstalls etc.

        :return: A text reason for why it was skipped, or None.
        """
        # Check whether to upgrade/reinstall this req or not.
        req_to_install.check_if_exists()
        if req_to_install.satisfied_by:
            upgrade_allowed = self._is_upgrade_allowed(req_to_install)

            # Is the best version is installed.
            best_installed = False

            if upgrade_allowed:
                # For link based requirements we have to pull the
                # tree down and inspect to assess the version #, so
                # its handled way down.
                should_check_possibility_for_upgrade = not (
                    requirement_set.force_reinstall or req_to_install.link
                )
                if should_check_possibility_for_upgrade:
                    try:
                        self.finder.find_requirement(
                            req_to_install, upgrade_allowed)
                    except BestVersionAlreadyInstalled:
                        best_installed = True
                    except DistributionNotFound:
                        # No distribution found, so we squash the
                        # error - it will be raised later when we
                        # re-try later to do the install.
                        # Why don't we just raise here?
                        pass

                if not best_installed:
                    # don't uninstall conflict if user install and
                    # conflict is not user install
                    if not (requirement_set.use_user_site and not
                            dist_in_usersite(req_to_install.satisfied_by)):
                        req_to_install.conflicts_with = \
                            req_to_install.satisfied_by
                    req_to_install.satisfied_by = None

            # Figure out a nice message to say why we're skipping this.
            if best_installed:
                skip_reason = 'already up-to-date'
            elif self.upgrade_strategy == "only-if-needed":
                skip_reason = 'not upgraded as not directly required'
            else:
                skip_reason = 'already satisfied'

            return skip_reason
        else:
            return None

    def _resolve_one(self, requirement_set, req_to_install,
                     require_hashes=False, ignore_dependencies=False):
        """Prepare a single requirements file.

        :return: A list of additional InstallRequirements to also install.
        """
        # Tell user what we are doing for this requirement:
        # obtain (editable), skipping, processing (local url), collecting
        # (remote url or package name)
        if req_to_install.constraint or req_to_install.prepared:
            return []

        req_to_install.prepared = True

        # ###################### #
        # # print log messages # #
        # ###################### #
        if req_to_install.editable:
            logger.info('Obtaining %s', req_to_install)
        else:
            # satisfied_by is only evaluated by calling _check_skip_installed,
            # so it must be None here.
            assert req_to_install.satisfied_by is None
            if not requirement_set.ignore_installed:
                skip_reason = self._check_skip_installed(
                    req_to_install, requirement_set
                )

            if req_to_install.satisfied_by:
                assert skip_reason is not None, (
                    '_check_skip_installed returned None but '
                    'req_to_install.satisfied_by is set to %r'
                    % (req_to_install.satisfied_by,))
                logger.info(
                    'Requirement %s: %s (%s)', skip_reason,
                    req_to_install,
                    req_to_install.satisfied_by.version)
            else:
                if (req_to_install.link and
                        req_to_install.link.scheme == 'file'):
                    path = url_to_path(req_to_install.link.url)
                    logger.info('Processing %s', display_path(path))
                else:
                    logger.info('Collecting %s', req_to_install)

        with indent_log():
            # ################################ #
            # # vcs update or unpack archive # #
            # ################################ #
            if req_to_install.editable:
                if require_hashes:
                    raise InstallationError(
                        'The editable requirement %s cannot be installed when '
                        'requiring hashes, because there is no single file to '
                        'hash.' % req_to_install)
                req_to_install.ensure_has_source_dir(requirement_set.src_dir)
                req_to_install.update_editable(not requirement_set.is_download)
                abstract_dist = make_abstract_dist(req_to_install)
                abstract_dist.prep_for_dist()
                if requirement_set.is_download:
                    req_to_install.archive(requirement_set.download_dir)
                req_to_install.check_if_exists()
            elif req_to_install.satisfied_by:
                if require_hashes:
                    logger.debug(
                        'Since it is already installed, we are trusting this '
                        'package without checking its hash. To ensure a '
                        'completely repeatable environment, install into an '
                        'empty virtualenv.')
                abstract_dist = Installed(req_to_install)
            else:
                # @@ if filesystem packages are not marked
                # editable in a req, a non deterministic error
                # occurs when the script attempts to unpack the
                # build directory
                req_to_install.ensure_has_source_dir(requirement_set.build_dir)
                # If a checkout exists, it's unwise to keep going.  version
                # inconsistencies are logged later, but do not fail the
                # installation.
                # FIXME: this won't upgrade when there's an existing
                # package unpacked in `req_to_install.source_dir`
                # package unpacked in `req_to_install.source_dir`
                if os.path.exists(
                        os.path.join(req_to_install.source_dir, 'setup.py')):
                    raise PreviousBuildDirError(
                        "pip can't proceed with requirements '%s' due to a"
                        " pre-existing build directory (%s). This is "
                        "likely due to a previous installation that failed"
                        ". pip is being responsible and not assuming it "
                        "can delete this. Please delete it and try again."
                        % (req_to_install, req_to_install.source_dir)
                    )
                req_to_install.populate_link(
                    self.finder,
                    self._is_upgrade_allowed(req_to_install),
                    require_hashes
                )
                # We can't hit this spot and have populate_link return None.
                # req_to_install.satisfied_by is None here (because we're
                # guarded) and upgrade has no impact except when satisfied_by
                # is not None.
                # Then inside find_requirement existing_applicable -> False
                # If no new versions are found, DistributionNotFound is raised,
                # otherwise a result is guaranteed.
                assert req_to_install.link
                link = req_to_install.link

                # Now that we have the real link, we can tell what kind of
                # requirements we have and raise some more informative errors
                # than otherwise. (For example, we can raise VcsHashUnsupported
                # for a VCS URL rather than HashMissing.)
                if require_hashes:
                    # We could check these first 2 conditions inside
                    # unpack_url and save repetition of conditions, but then
                    # we would report less-useful error messages for
                    # unhashable requirements, complaining that there's no
                    # hash provided.
                    if is_vcs_url(link):
                        raise VcsHashUnsupported()
                    elif is_file_url(link) and is_dir_url(link):
                        raise DirectoryUrlHashUnsupported()
                    if (not req_to_install.original_link and
                            not req_to_install.is_pinned):
                        # Unpinned packages are asking for trouble when a new
                        # version is uploaded. This isn't a security check, but
                        # it saves users a surprising hash mismatch in the
                        # future.
                        #
                        # file:/// URLs aren't pinnable, so don't complain
                        # about them not being pinned.
                        raise HashUnpinned()
                hashes = req_to_install.hashes(
                    trust_internet=not require_hashes)
                if require_hashes and not hashes:
                    # Known-good hashes are missing for this requirement, so
                    # shim it with a facade object that will provoke hash
                    # computation and then raise a HashMissing exception
                    # showing the user what the hash should be.
                    hashes = MissingHashes()

                try:
                    download_dir = requirement_set.download_dir
                    # We always delete unpacked sdists after pip ran.
                    autodelete_unpacked = True
                    if req_to_install.link.is_wheel \
                            and requirement_set.wheel_download_dir:
                        # when doing 'pip wheel` we download wheels to a
                        # dedicated dir.
                        download_dir = requirement_set.wheel_download_dir
                    if req_to_install.link.is_wheel:
                        if download_dir:
                            # When downloading, we only unpack wheels to get
                            # metadata.
                            autodelete_unpacked = True
                        else:
                            # When installing a wheel, we use the unpacked
                            # wheel.
                            autodelete_unpacked = False
                    unpack_url(
                        req_to_install.link, req_to_install.source_dir,
                        download_dir, autodelete_unpacked,
                        session=requirement_set.session, hashes=hashes,
                        progress_bar=requirement_set.progress_bar)
                except requests.HTTPError as exc:
                    logger.critical(
                        'Could not install requirement %s because '
                        'of error %s',
                        req_to_install,
                        exc,
                    )
                    raise InstallationError(
                        'Could not install requirement %s because '
                        'of HTTP error %s for URL %s' %
                        (req_to_install, exc, req_to_install.link)
                    )
                abstract_dist = make_abstract_dist(req_to_install)
                abstract_dist.prep_for_dist()
                if requirement_set.is_download:
                    # Make a .zip of the source_dir we already created.
                    if req_to_install.link.scheme in vcs.all_schemes:
                        req_to_install.archive(requirement_set.download_dir)
                # req_to_install.req is only avail after unpack for URL
                # pkgs repeat check_if_exists to uninstall-on-upgrade
                # (#14)
                if not requirement_set.ignore_installed:
                    req_to_install.check_if_exists()
                if req_to_install.satisfied_by:
                    should_modify = (
                        self.upgrade_strategy != "not-allowed" or
                        requirement_set.ignore_installed
                    )
                    if should_modify:
                        # don't uninstall conflict if user install and
                        # conflict is not user install
                        if not (requirement_set.use_user_site and not
                                dist_in_usersite(
                                    req_to_install.satisfied_by)):
                            req_to_install.conflicts_with = \
                                req_to_install.satisfied_by
                        req_to_install.satisfied_by = None
                    else:
                        logger.info(
                            'Requirement already satisfied (use '
                            '--upgrade to upgrade): %s',
                            req_to_install,
                        )

            # register tmp src for cleanup in case something goes wrong
            requirement_set.reqs_to_cleanup.append(req_to_install)

            # ###################### #
            # # parse dependencies # #
            # ###################### #

            dist = abstract_dist.dist(self.finder)
            try:
                check_dist_requires_python(dist)
            except UnsupportedPythonVersion as err:
                if requirement_set.ignore_requires_python:
                    logger.warning(err.args[0])
                else:
                    raise
            more_reqs = []

            def add_req(subreq, extras_requested):
                sub_install_req = InstallRequirement.from_req(
                    str(subreq),
                    req_to_install,
                    isolated=requirement_set.isolated,
                    wheel_cache=requirement_set._wheel_cache,
                )
                more_reqs.extend(
                    requirement_set.add_requirement(
                        sub_install_req, req_to_install.name,
                        extras_requested=extras_requested
                    )
                )

            # We add req_to_install before its dependencies, so that we
            # can refer to it when adding dependencies.
            if not requirement_set.has_requirement(req_to_install.name):
                # 'unnamed' requirements will get added here
                requirement_set.add_requirement(req_to_install, None)

            if not ignore_dependencies:
                if req_to_install.extras:
                    logger.debug(
                        "Installing extra requirements: %r",
                        ','.join(req_to_install.extras),
                    )
                missing_requested = sorted(
                    set(req_to_install.extras) - set(dist.extras)
                )
                for missing in missing_requested:
                    logger.warning(
                        '%s does not provide the extra \'%s\'',
                        dist, missing
                    )

                available_requested = sorted(
                    set(dist.extras) & set(req_to_install.extras)
                )
                for subreq in dist.requires(available_requested):
                    add_req(subreq, extras_requested=available_requested)

            if not req_to_install.editable and not req_to_install.satisfied_by:
                # XXX: --no-install leads this to report 'Successfully
                # downloaded' for only non-editable reqs, even though we took
                # action on them.
                requirement_set.successfully_downloaded.append(req_to_install)

        return more_reqs
