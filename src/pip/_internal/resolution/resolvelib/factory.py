import collections

from pip._vendor import six
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import (
    InstallationError,
    UnsupportedPythonVersion,
)
from pip._internal.utils.misc import (
    dist_in_site_packages,
    dist_in_usersite,
    get_installed_distributions,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.virtualenv import running_under_virtualenv

from .candidates import (
    AlreadyInstalledCandidate,
    EditableCandidate,
    ExtrasCandidate,
    LinkCandidate,
    RequiresPythonCandidate,
)
from .requirements import (
    ExplicitRequirement,
    RequiresPythonRequirement,
    SpecifierRequirement,
)

if MYPY_CHECK_RUNNING:
    from typing import Dict, Iterator, Optional, Set, Tuple, TypeVar

    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.version import _BaseVersion
    from pip._vendor.pkg_resources import Distribution
    from pip._vendor.resolvelib import ResolutionImpossible

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.models.link import Link
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.resolution.base import InstallRequirementProvider

    from .base import Candidate, Requirement
    from .candidates import BaseCandidate

    C = TypeVar("C")
    Cache = Dict[Link, C]
    VersionCandidates = Dict[_BaseVersion, Candidate]


class Factory(object):
    def __init__(
        self,
        finder,  # type: PackageFinder
        preparer,  # type: RequirementPreparer
        make_install_req,  # type: InstallRequirementProvider
        use_user_site,  # type: bool
        force_reinstall,  # type: bool
        ignore_installed,  # type: bool
        ignore_requires_python,  # type: bool
        py_version_info=None,  # type: Optional[Tuple[int, ...]]
    ):
        # type: (...) -> None

        self.finder = finder
        self.preparer = preparer
        self._python_candidate = RequiresPythonCandidate(py_version_info)
        self._make_install_req_from_spec = make_install_req
        self._use_user_site = use_user_site
        self._force_reinstall = force_reinstall
        self._ignore_requires_python = ignore_requires_python

        self._link_candidate_cache = {}  # type: Cache[LinkCandidate]
        self._editable_candidate_cache = {}  # type: Cache[EditableCandidate]

        if not ignore_installed:
            self._installed_dists = {
                canonicalize_name(dist.project_name): dist
                for dist in get_installed_distributions()
            }
        else:
            self._installed_dists = {}

    def _make_candidate_from_dist(
        self,
        dist,  # type: Distribution
        extras,  # type: Set[str]
        parent,  # type: InstallRequirement
    ):
        # type: (...) -> Candidate
        base = AlreadyInstalledCandidate(dist, parent, factory=self)
        if extras:
            return ExtrasCandidate(base, extras)
        return base

    def _make_candidate_from_link(
        self,
        link,          # type: Link
        extras,        # type: Set[str]
        parent,        # type: InstallRequirement
        name=None,     # type: Optional[str]
        version=None,  # type: Optional[_BaseVersion]
    ):
        # type: (...) -> Candidate
        # TODO: Check already installed candidate, and use it if the link and
        # editable flag match.
        if parent.editable:
            if link not in self._editable_candidate_cache:
                self._editable_candidate_cache[link] = EditableCandidate(
                    link, parent, factory=self, name=name, version=version,
                )
            base = self._editable_candidate_cache[link]  # type: BaseCandidate
        else:
            if link not in self._link_candidate_cache:
                self._link_candidate_cache[link] = LinkCandidate(
                    link, parent, factory=self, name=name, version=version,
                )
            base = self._link_candidate_cache[link]
        if extras:
            return ExtrasCandidate(base, extras)
        return base

    def iter_found_candidates(self, ireq, extras):
        # type: (InstallRequirement, Set[str]) -> Iterator[Candidate]
        name = canonicalize_name(ireq.req.name)

        # We use this to ensure that we only yield a single candidate for
        # each version (the finder's preferred one for that version). The
        # requirement needs to return only one candidate per version, so we
        # implement that logic here so that requirements using this helper
        # don't all have to do the same thing later.
        candidates = collections.OrderedDict()  # type: VersionCandidates

        # Yield the installed version, if it matches, unless the user
        # specified `--force-reinstall`, when we want the version from
        # the index instead.
        installed_version = None
        if not self._force_reinstall and name in self._installed_dists:
            installed_dist = self._installed_dists[name]
            installed_version = installed_dist.parsed_version
            if ireq.req.specifier.contains(
                installed_version,
                prereleases=True
            ):
                candidate = self._make_candidate_from_dist(
                    dist=installed_dist,
                    extras=extras,
                    parent=ireq,
                )
                candidates[installed_version] = candidate

        found = self.finder.find_best_candidate(
            project_name=ireq.req.name,
            specifier=ireq.req.specifier,
            hashes=ireq.hashes(trust_internet=False),
        )
        for ican in found.iter_applicable():
            if ican.version == installed_version:
                continue
            candidate = self._make_candidate_from_link(
                link=ican.link,
                extras=extras,
                parent=ireq,
                name=name,
                version=ican.version,
            )
            candidates[ican.version] = candidate

        return six.itervalues(candidates)

    def make_requirement_from_install_req(self, ireq):
        # type: (InstallRequirement) -> Requirement
        if ireq.link:
            # TODO: Get name and version from ireq, if possible?
            #       Specifically, this might be needed in "name @ URL"
            #       syntax - need to check where that syntax is handled.
            cand = self._make_candidate_from_link(
                ireq.link, extras=set(ireq.extras), parent=ireq,
            )
            return ExplicitRequirement(cand)
        return SpecifierRequirement(ireq, factory=self)

    def make_requirement_from_spec(self, specifier, comes_from):
        # type: (str, InstallRequirement) -> Requirement
        ireq = self._make_install_req_from_spec(specifier, comes_from)
        return self.make_requirement_from_install_req(ireq)

    def make_requires_python_requirement(self, specifier):
        # type: (Optional[SpecifierSet]) -> Optional[Requirement]
        if self._ignore_requires_python or specifier is None:
            return None
        return RequiresPythonRequirement(specifier, self._python_candidate)

    def should_reinstall(self, candidate):
        # type: (Candidate) -> bool
        # TODO: Are there more cases this needs to return True? Editable?
        dist = self._installed_dists.get(candidate.name)
        if dist is None:  # Not installed, no uninstallation required.
            return False

        # We're installing into global site. The current installation must
        # be uninstalled, no matter it's in global or user site, because the
        # user site installation has precedence over global.
        if not self._use_user_site:
            return True

        # We're installing into user site. Remove the user site installation.
        if dist_in_usersite(dist):
            return True

        # We're installing into user site, but the installed incompatible
        # package is in global site. We can't uninstall that, and would let
        # the new user installation to "shadow" it. But shadowing won't work
        # in virtual environments, so we error out.
        if running_under_virtualenv() and dist_in_site_packages(dist):
            raise InstallationError(
                "Will not install to the user site because it will "
                "lack sys.path precedence to {} in {}".format(
                    dist.project_name, dist.location,
                )
            )
        return False

    def _report_requires_python_error(
        self,
        requirement,  # type: RequiresPythonRequirement
        parent,  # type: Candidate
    ):
        # type: (...) -> UnsupportedPythonVersion
        template = (
            "Package {package!r} requires a different Python: "
            "{version} not in {specifier!r}"
        )
        message = template.format(
            package=parent.name,
            version=self._python_candidate.version,
            specifier=str(requirement.specifier),
        )
        return UnsupportedPythonVersion(message)

    def get_installation_error(self, e):
        # type: (ResolutionImpossible) -> Optional[InstallationError]
        for cause in e.causes:
            if isinstance(cause.requirement, RequiresPythonRequirement):
                return self._report_requires_python_error(
                    cause.requirement,
                    cause.parent,
                )
        return None
