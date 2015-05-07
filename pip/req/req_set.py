from __future__ import absolute_import

from collections import defaultdict
import functools
import itertools
import logging
import os
import sys

from pip._vendor import pkg_resources
from pip._vendor import requests
from pip._vendor.packaging import specifiers, version as pkg_version

import pip
from pip.download import (url_to_path, unpack_url)
from pip.exceptions import (InstallationError, BestVersionAlreadyInstalled,
                            DistributionNotFound, PreviousBuildDirError)
from pip.req.req_install import InstallRequirement
from pip.utils import (
    display_path, dist_in_usersite, ensure_dir, normalize_path)
from pip.utils.logging import indent_log
from pip.vcs import vcs


logger = logging.getLogger(__name__)


class BackTrack(InstallationError):
    pass


class Requirements(object):

    def __init__(self):
        self._keys = []
        self._dict = {}
        # Mapping of alias: real_name
        self.aliases = {}

    def keys(self):
        return self._keys

    def values(self):
        return [self._dict[key] for key in self._keys]

    def __contains__(self, item):
        return item in self._keys

    def __setitem__(self, key, value):
        if key not in self._keys:
            self._keys.append(key)
        self._dict[key] = value

    def __getitem__(self, key):
        return self._dict[key]

    def get(self, project_name, *args):
        for name in project_name, project_name.lower():
            if name in self:
                return self[name]
            if name in self.aliases:
                return self[self.aliases[name]]
        if args:
            return args[0]
        else:
            raise KeyError("No project with the name %r" % project_name)

    def __repr__(self):
        values = ['%s: %s' % (repr(k), repr(self[k])) for k in self.keys()]
        return 'Requirements({%s})' % ', '.join(values)


class DistAbstraction(object):
    """Abstracts out the wheel vs non-wheel prepare_files logic.

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


def make_abstract_dist(req_to_install):
    """Factory to make an abstract dist object.

    Preconditions: Either an editable req with code checked out, or
    satisfied_by or a wheel link, or a non-editable req with code present on
    disk.

    :return: A concrete DistAbstraction.
    """
    if req_to_install.editable:
        return IsSDist(req_to_install)
    elif req_to_install.link and req_to_install.link.is_wheel:
        return IsWheel(req_to_install)
    else:
        return IsSDist(req_to_install)


class IsWheel(DistAbstraction):

    def dist(self, finder):
        return list(pkg_resources.find_distributions(
            self.req_to_install.build_path))[0]

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


class RequirementSet(object):

    def __init__(self, req_cache, download_dir, upgrade=False,
                 ignore_installed=False, as_egg=False, target_dir=None,
                 ignore_dependencies=False, force_reinstall=False,
                 use_user_site=False, session=None, pycompile=True,
                 isolated=False, wheel_download_dir=None,
                 wheel_cache=None):
        """Create a RequirementSet.

        :param use_user_site: If True, install into the user home directory
            (rather than site-packages).
        :param wheel_download_dir: Where still-packed .whl files should be
            written to. If None they are written to the download_dir parameter.
            Separate to download_dir to permit only keeping wheel archives for
            pip wheel.
        :param download_dir: Where still packed archives should be written to.
            If None they are not saved, and are deleted immediately after
            unpacking.
        :param wheel_cache: The pip wheel cache, for passing to
            InstallRequirement.
        """
        for name in ["session", "req_cache"]:
            if locals().get(name, None) is None:
                raise TypeError(
                    "RequirementSet() missing 1 required argument: "
                    "'%s'" % name
                )
        self.req_cache = req_cache
        # XXX: download_dir and wheel_download_dir overlap semantically and may
        # be combined if we're willing to have non-wheel archives present in
        # the wheelhouse output by 'pip wheel'.
        self.download_dir = download_dir
        self.upgrade = upgrade
        self.ignore_installed = ignore_installed
        self.force_reinstall = force_reinstall
        self.requirements = Requirements()
        self.unnamed_requirements = []
        self.ignore_dependencies = ignore_dependencies
        self.successfully_downloaded = []
        self.successfully_installed = []
        self.as_egg = as_egg
        self.use_user_site = use_user_site
        self.target_dir = target_dir  # set from --target option
        self.session = session
        self.pycompile = pycompile
        self.isolated = isolated
        if wheel_download_dir:
            wheel_download_dir = normalize_path(wheel_download_dir)
        self.wheel_download_dir = wheel_download_dir
        self._wheel_cache = wheel_cache
        # Maps from install_req -> dependencies_of_install_req
        self._dependencies = defaultdict(list)

    def __str__(self):
        reqs = [req for req in self.requirements.values()
                if not req.comes_from]
        reqs.sort(key=lambda req: req.name.lower())
        return ' '.join([str(req.req) for req in reqs])

    def __repr__(self):
        reqs = [req for req in self.requirements.values()]
        reqs.sort(key=lambda req: req.name.lower())
        reqs_str = ', '.join([str(req.req) for req in reqs])
        return ('<%s object; %d requirement(s): %s>'
                % (self.__class__.__name__, len(reqs), reqs_str))

    def add_requirement(self, install_req, parent_req_name=None):
        """Add install_req as a requirement to install.

        :param parent_req_name: The name of the requirement that needed this
            added. The name is used because when multiple unnamed requirements
            resolve to the same name, we could otherwise end up with dependency
            links that point outside the Requirements set. parent_req must
            already be added. Note that None implies that this is a user
            supplied requirement, vs an inferred one.
        :return: Additional requirements to scan. That is either [] if
            the requirement is not applicable, or [install_req] if the
            requirement is applicable and has just been added.
        """
        name = install_req.name
        if not install_req.match_markers():
            logger.warning("Ignoring %s: markers %r don't match your "
                           "environment", install_req.name,
                           install_req.markers)
            return []

        install_req.as_egg = self.as_egg
        install_req.use_user_site = self.use_user_site
        install_req.target_dir = self.target_dir
        install_req.pycompile = self.pycompile
        if not install_req.req_cache:
            install_req.req_cache = self.req_cache
        if not name:
            # url or path requirement w/o an egg fragment
            self.unnamed_requirements.append(install_req)
            return [install_req]
        else:
            try:
                existing_req = self.get_requirement(name)
            except KeyError:
                existing_req = None
            if (parent_req_name is None and existing_req and not
                    existing_req.constraint):
                raise InstallationError(
                    'Double requirement given: %s (already in %s, name=%r)'
                    % (install_req, existing_req, name))
            if not existing_req:
                # Add requirement
                self.requirements[name] = install_req
                # FIXME: what about other normalizations?  E.g., _ vs. -?
                if name.lower() != name:
                    self.requirements.aliases[name.lower()] = name
                result = [install_req]
            else:
                if not existing_req.constraint:
                    # No need to scan, we've already encountered this for
                    # scanning.
                    result = []
                elif not install_req.constraint:
                    # If we're now installing a constraint, mark the existing
                    # object for real installation.
                    existing_req.constraint = False
                    # And now we need to scan this.
                    result = [existing_req]
                # Canonicalise to the already-added object for the backref
                # check below.
                install_req = existing_req
            if parent_req_name:
                parent_req = self.get_requirement(parent_req_name)
                self._dependencies[parent_req].append(install_req)
            return result

    def has_requirement(self, project_name):
        for name in project_name, project_name.lower():
            if name in self.requirements or name in self.requirements.aliases:
                return True
        return False

    @property
    def has_requirements(self):
        return list(req for req in self.requirements.values() if not
                    req.constraint) or self.unnamed_requirements

    @property
    def is_download(self):
        if self.download_dir:
            self.download_dir = os.path.expanduser(self.download_dir)
            if os.path.exists(self.download_dir):
                return True
            else:
                logger.critical('Could not find download directory')
                raise InstallationError(
                    "Could not find or access download directory '%s'"
                    % display_path(self.download_dir))
        return False

    def get_requirement(self, project_name):
        return self.requirements.get(project_name)

    def get_versions(self, name, specifier=None):
        """Get the full set of versions to consider for this req-set.

        :param name: The name of the distribution.
        :param specifier: If supplied, a constraint to apply *globally* to this
            req-set. Should only be used for constraints that apply to all
            paths (rather than those introduced by a candidate version).
        :return: Ordered list in best-first order of Versions.
        """
        result = self._versions.get(name, None)
        if result is not None:
            # Multiple global filters not implemented yet.
            assert specifier is None
            return result
        result = self.req_cache.get_versions(
            name, self.upgrade, not self.force_reinstall)
        if specifier is not None:
            # XXX: BEFORE MERGE: must preserve dev versions when one is already
            # installed. E.g. pip 7.0.0.dev is installed, don't downgrade to
            # 6.1.1 just because there is a requirement on 'pip' in the global
            # reqs.
            result_prime = tuple(specifier.filter(result))
            if not result_prime:
                raise DistributionNotFound(
                    "No versions of %s after applying global constraint %s "
                    "to %s" % (name, specifier, result))
            logger.debug("Trimmed %s versions to %s" % (name, result_prime))
            result = result_prime
        self._versions[name] = result
        return result

    def uninstall(self, auto_confirm=False):
        for req in self.requirements.values():
            if req.constraint:
                continue
            req.uninstall(auto_confirm=auto_confirm)
            req.commit_uninstall()

    def prepare_files(self, finder):
        """
        Prepare process. Create temp directories, download and/or unpack files.

        RESOLVE
        """
        # make the wheelhouse
        if self.wheel_download_dir:
            ensure_dir(self.wheel_download_dir)
        # We apply global constraints that trim the search space,
        # self._versions contains such trims.
        self._versions = {}
        # Allow for a decent # of reqs
        # Each dep in the graph is a frame.
        sys.setrecursionlimit(5000)
        # constraints model:
        # There can be only one instance of a given name.
        # There can be multiple extras for a given name.
        # There can be multiple version specifiers for a given name.
        # Nothing else is relevant to the selection process.
        # (e.g. editability doesn't alter it).
        constraints = {} # type: Dict[name, Tuple[[extraname], SpecifierSet]]
        pending = set() # type: Set[Tuple[name, [extraname], SpecifierSet]]
        # We need to map from InstallRequirement to constraints:
        for req_to_install in self.unnamed_requirements:
            name, extras, specifier = self._req_meta(req_to_install, finder)
            # unnamed requirements are not resolvable, they Just Are.
            if name in constraints:
                raise InstallationError('Double requirement given: %s', name)
            pending.add((name, extras, specifier))
            # Unammed requirements are pinned by req_install.dist.
        for req_to_install in self.requirements.values():
            name, extras, specifier = self._req_meta(req_to_install, finder)
            # This may be relaxed in future to just check compatibility
            # but for now everything supplied must be unique.
            if name in constraints:
                raise InstallationError('Double requirement given: %s', name)
            pending.add((name, extras, specifier))
            # Limit the versions of name to consider to those specified
            # globally.
            self.get_versions(name, specifier)
        # If this top level call fails, we couldn't resolve all the pending
        # items.
        # type: Dict[name, Tuple[[extraname], version.Version]]
        # extras are in chosen, so that when a dep on different extras is
        # found we can add those in.
        steps, chosen = self.resolve_constraints(0, constraints, {}, pending)
        # We lookup options that the user supplied in the user requirements.
        reference_requirements = self.requirements
        self.requirements = Requirements()
        # Topologically sort the things we're going to install. We break
        # cycles at an arbitrary point and make no other gurantees.
        order = []
        ordered_names = set()
        def schedule(item):
            name, (extras, version) = item
            if name in ordered_names:
                return
            ordered_names.add(name)
            if self.ignore_dependencies:
                requires = []
            else:
                requires = self.req_cache.requires(
                    name, extras, version, not self.force_reinstall)
            for req_name, _, _ in requires:
                req_chosen = chosen[req_name]
                schedule((req_name, req_chosen))
            order.append(name)
        for item in chosen.items():
            schedule(item)
        for name in order:
            extras, version = chosen[name]
            if extras:
                extra_string = "[" + ",".join(extras) + "]"
            else:
                extra_string = ""
            candidate = self.req_cache.candidate_from_version(name, version)
            installed = self.req_cache.installed(name, version)
            editable = None
            editable_options = None
            options = None
            if installed:
                link = None
                cached_req = None
            else:
                link = candidate.location
                canonical_name = pkg_resources.safe_name(name).lower()
                cached_req = self.req_cache.lookup_name(canonical_name, version)
                editable = cached_req.editable
                editable_options = cached_req._editable_options
                user_req = reference_requirements.get(name, None)
                if user_req:
                    options = user_req.options
                # Must have figured out version and name by now.
                assert cached_req.version
                assert cached_req.name
            req = InstallRequirement(
                "%s%s===%s" % (name, extra_string, version), None,
                isolated=self.isolated,
                wheel_cache=self._wheel_cache,
                link=link,
                editable=editable,
                editable_options=editable_options,
                options=options)
            req._cached_req = cached_req
            req.use_user_site = self.use_user_site
            req.target_dir = self.target_dir
            req.pycompile = self.pycompile
            req.as_egg = self.as_egg
            # Fill out conflicts_with to detect when we need to uninstall.
            req.check_if_exists()
            if installed:
                if not self.upgrade:
                    req.skip_reason = 'satisfied (use --upgrade to upgrade)'
                else:
                    req.skip_reason = 'up-to-date'
            self.add_requirement(req)
        logger.debug("Resolved %s packages in %s steps.",
            len(chosen), steps)

    def resolve_constraints(self, steps, constraints, chosen, pending):
        """Find a set of packages for pending thats fits constraints.

        :param steps: The steps taken so far.
        :param constraints: The constraints to choose under. A dict of
            name -> tuple(tuple(extranames), specifierset)
        :param chosen: The currently chosen requirements. A dict of
            name -> tuple(tuple(extranames), version)
        :param pending: A set of (name, tuple(extranames), specifier)
            dependencies that have yet to be processed.

        constraints, chosen and pending are not mutated.

        :return: steps, successfully chosen versions.
        :raises: BackTrack if the constraints cannot be solved.
        """
        # The current implementation is recursive: the stack contains
        # the path through the solution space being taken. If the frame is the
        # first one to attempt a given requirement (the req is not in chosen)
        # then it will iterate through installed,newest-oldest and attempt each
        # version. When conflicts occur a Backtrace is thrown; that propogates
        # up until the conflicting package (or those that influenced its
        # inclusion) intersects with the package being iterated either directly
        # or on dependencies. Since this is NPC, we cap the total steps at a
        # reasonable number: if its doing to die of heat-death, we'll hit the
        # cap.
        # So this picks a req, does 'for version in versions: subreq' - loop of
        # loop of loops etc. One particular downside of this is that if the
        # current installed version of the first thing probed has to be
        # upgraded to meet the users request - which can happen when they
        # include that thing in their constraints - we'll end up
        # considering every other possible version of everything before trying
        # the latest version of that thing. A possibly better strategy would be
        # to try a broad search: rather than nested loops, try the latest
        # across the surface area, then bump one version down of each, etc.
        # But this requires a much more sophisticated way of tracking which
        # combinations have been tried (since latest A and oldest B may still
        # be needed as the winning combination), and we don't know the set of
        # things whose versions we need to try a-priori, since any version
        # we consider can add new requirements to the mix.
        # Doing this would reduce some of the pathology with things like
        # youtube-dl which has hundreds of versions, and can end up in the
        # inner loop of a search otherwise. Sorting by version count can reduce
        # that, but it has corner cases (such as a top level thing conflicting
        # with a thing with only one item) that make it not very effective.
        if not pending:
            return steps, chosen
        steps += 1
        step_limit = 100000
        if steps > step_limit:
            # Package selection worst case is NP-Complete: bail if it looks
            # like we're getting nowhere.
            logger.error(
                "Hit step limit during resolving, %f choices from %d "
                "versions in %d packages after %d steps" %
                (self.req_cache.guess_scale() + (step_limit,)))
            raise InstallationError(
                "Hit step limit during requirement resolving.")
        constraint = frozenset(itertools.islice(pending, 0, 1))
        new_pending = pending.difference(constraint)
        name, extras, specifier = list(constraint)[0]
        logger.debug("Evaluating %s%s %s" % (name, extras, specifier))
        if name in constraints:
            co_constraint = constraints[name]
            specifier &= co_constraint[1]
            extras = extras + co_constraint[0]
        if name in chosen:
            if not specifier.contains(chosen[name][1]):
                msg = ("version %s of %s not compatible with %s" %
                       (chosen[name][1], name, specifier))
                logger.debug("Backtracking: %s" % msg)
                raise BackTrack(msg, [name], steps)
            extras = extras + chosen[name][0]
        # the constraint isn't known to be incompatible.
        # 1) turn it into a constraint for next steps to consider
        constraints = constraints.copy()
        constraints[name] = (tuple(sorted(set(extras))), specifier)
        chosen = chosen.copy()
        if name in chosen:
            # We checked above for compat.
            # Whatever frame added name will do probing in the event
            # of failures. Merge extras and cast forward.
            # XXX: Possible memory pressure optimisation: test extras for
            # difference before copying chosen.
            chosen[name] = (
                tuple(sorted(set(extras + chosen[name][0]))), chosen[name][1])
            return self.resolve_constraints(
                steps, constraints, chosen, new_pending)
        # Loop over all possible versions in preference order.
        last_error = None
        requires = ()
        # DEEP FUTURE: Also trim by any globally applicable constraints -
        # e.g. if some version of name is required, and are three versions of
        # name, combine all their requirements to get any space trimming we can
        # for instance, if we globally need fred, and there are two versions of
        # fred, and one requires bar >=1.0 <2, and te other requires bar >=1.5
        # <3, then we can globally trim bar <1.0 >=3 without prejuidice to
        # local constraints that may be added later/from other names.
        # if self.must_include(name):
        #    self.global_trim(name, versions)
        # FUTURE: For now, a limited version of this:
        # if name in unnamed_requirements or named_requirements:
        # -> globally needed
        # if len(get_versions(name)) == 1:
        #   for requirements in requires...
        #     globally_trim_that_requirment
        for candidate in self.get_versions(name):
            logger.debug("Trying %s %s" % (name, candidate))
            if not specifier.contains(candidate):
                # Incompatible with existing constraints.
                msg = "%s %s incompatible with %s" % (
                    name, candidate, specifier)
                logger.debug(msg)
                continue
            chosen[name] = (extras, candidate)
            if self.ignore_dependencies:
                requires = ()
            else:
                try:
                    requires = self.req_cache.requires(
                        name, extras, candidate, not self.force_reinstall)
                except InstallationError:
                    # Cannot build the egg_info etc.
                    # TODO: remove this version so we don't try again.
                    msg = "Cannot get requirements for %s(%s)" % (name, candidate)
                    logger.debug('Backtracking: %s' % msg)
                    continue
            try_pending = set(requires)
            try:
                return self.resolve_constraints(
                    steps, constraints, chosen, new_pending.union(try_pending))
            except BackTrack as e:
                # If the error occured on an additional constraint for name
                # or on a package that this candidate chose, then its worth
                # trying a different version. Otherwise, the root of the
                # failure is higher up.
                failed_names = e.args[1]
                found = name in failed_names
                req_names = set([req_name for (req_name, _, _) in requires])
                if req_names.intersection(failed_names):
                    found = True
                if not found:
                    # We neither introduced, nor are, the failed requirement
                    # (or any that introduced/are it and cascaded).
                    # Therefor all the involved entries must have come from
                    # above: cascade as-is.
                    logger.debug(
                        "Backtracking: not found %s from %s(%s)", failed_names,
                        name, req_names)
                    raise e
                last_error = e
                steps = e.args[2]
        if last_error:
            msg = "No versions of %s could have its requirements met." % name
            logger.debug('Backtracking: %s' % msg)
            # We need to reference the package that failed further down, so
            # that higher choices which conflict with lower constraints 
            # can correctly detect and iterate.
            # XXX: Do we need to add req_names in here? Not yet reasoned
            # through.
            raise BackTrack(msg, [name] + e.args[1], steps)
            # XXX: six.reraise ?
        # We've failed to find a version matching the requires our versions
        # have: this might be because existing constraints from above us
        # conflict with them, so their names need to be present (otherwise
        # we would cascade past a point where iterating might work).
        msg = "No versions of %s match the constraints %s" % (name, specifier)
        logger.debug(msg)
        names = [name] + [req_name for (req_name, _, _) in requires]
        raise BackTrack(msg, names, steps)

    def _req_specifier(self, req_to_install, finder): 
        if req_to_install.link is not None:
            # path/url based - build egg info.
            req_to_install.dist()
        specifier = req_to_install.req.specifier
        name = pkg_resources.safe_name(req_to_install.name).lower()
        if self.ignore_dependencies:
            extras = ()
        else:
            extras = tuple(sorted(set(req_to_install.extras)))
        return name, extras, specifier

    def _req_meta(self, req_to_install, finder):
        """get the requirement if needed, figure out name and specifiers
        
        If the requirement specifies an exact version, the specifier returned
        will be a === specifier. All path and url based requirements have an
        implicit exact version.

        :param req_to_install: An InstallRequirement.
        :return: name, [extras], specifier.SpecifierSet.
        """
        logger.debug('Processing %s', req_to_install.trace_label())
        with indent_log():
            # satisfied_by is not evaluated at the point _req_meta is called:
            # so it must be None here. If it is not, something has changed and
            # the assumptions here would be violated.
            assert req_to_install.satisfied_by is None
            # ################################ #
            # # vcs update or unpack archive # #
            # ################################ #
            # @@ if filesystem packages are not marked
            # editable in a req, a non deterministic error
            # occurs when the script attempts to unpack the
            # build directory.
            if req_to_install.link is None:
                return self._req_specifier(req_to_install, finder)
            # url/path
            if req_to_install.editable:
                logger.debug('Obtaining %s', req_to_install)
                req_to_install.update_editable(not self.is_download)
            else:
                try:
                    download_dir = self.download_dir
                    # We always delete unpacked sdists after pip ran.
                    autodelete_unpacked = True
                    if req_to_install.link.is_wheel \
                            and self.wheel_download_dir:
                        # when doing 'pip wheel` we download wheels to a
                        # dedicated dir.
                        download_dir = self.wheel_download_dir
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
                        req_to_install.link, req_to_install.build_path,
                        download_dir, autodelete_unpacked,
                        session=self.session)
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

            if (self.is_download and req_to_install.editable or
                req_to_install.link.scheme in vcs.all_schemes):
                # Make a .zip of the build_path we already created.
                # Build egg info if needed to determine name and version.
                result = self._req_specifier(req_to_install, finder)
                req_to_install._cached_req.archive(self.download_dir)
                return result
            return self._req_specifier(req_to_install, finder)

    def install(self, install_options, global_options=(), *args, **kwargs):
        """
        Install everything in this set (after having downloaded and unpacked
        the packages)
        """
        # Ordered by prepare_files.
        ordered = self.requirements.values()
        # Strip out already installed (and thus no-ops).
        to_install = []
        for req in ordered:
            if not self.force_reinstall and req.satisfied_by:
                logger.info(
                    'Requirement already %s: %s', req.skip_reason, req)
            else:
                to_install.append(req)

        if to_install:
            logger.info(
                'Installing collected packages: %s',
                ', '.join(
                    sorted(["%s(%s)" % (req.name, req._cached_req.version)
                           for req in to_install])))

        with indent_log():
            for requirement in to_install:
                if requirement.conflicts_with:
                    if self.ignore_installed:
                        logger.warning(
                            'Ignoring existing installation: %s',
                            requirement.conflicts_with)
                    else:
                        logger.info(
                            'Found existing installation: %s',
                            requirement.conflicts_with)
                        with indent_log():
                            requirement.uninstall(auto_confirm=True)
                try:
                    requirement.install(
                        install_options,
                        global_options,
                        *args,
                        **kwargs
                    )
                except:
                    # if install did not succeed, rollback previous uninstall
                    if (requirement.conflicts_with and not
                            requirement.install_succeeded):
                        requirement.rollback_uninstall()
                    raise
                else:
                    if (requirement.conflicts_with and
                            requirement.install_succeeded):
                        requirement.commit_uninstall()
                requirement.remove_temporary_source()

        self.successfully_installed = to_install
