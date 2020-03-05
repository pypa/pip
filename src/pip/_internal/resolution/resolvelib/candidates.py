from pip._vendor.packaging.utils import canonicalize_name

# TODO: Re-implement me.
from pip._internal.resolution.legacy.resolver import (
    UnsupportedPythonVersion,
    _check_dist_requires_python,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, Optional, Sequence, Set

    from pip._vendor.packaging.version import _BaseVersion
    from pip._vendor.pkg_resources import Distribution
    from pip._internal.distributions import AbstractDistribution
    from pip._internal.models.link import Link
    from pip._internal.req.req_install import InstallRequirement

    from .requirements import Requirement, ResolveOptions

    RequirementProvider = Callable[[str, InstallRequirement], Requirement]


def format_name(project, extras):
    # type: (str, Set[str]) -> str
    if not extras:
        return project
    canonical_extras = sorted(canonicalize_name(e) for e in extras)
    return "{}[{}]".format(project, ",".join(canonical_extras))


class Candidate(object):
    @property
    def name(self):
        # type: () -> str
        raise NotImplementedError("Override in subclass")

    @property
    def version(self):
        # type: () -> _BaseVersion
        raise NotImplementedError("Override in subclass")

    @property
    def link(self):
        # type: () -> Link
        raise NotImplementedError("Override in subclass")

    def get_dependencies(self, make_req):
        # type: (RequirementProvider) -> Sequence[Requirement]
        raise NotImplementedError("Override in subclass")


class ExtrasCandidate(Candidate):
    def __init__(self, candidate, extras):
        # type: (ConcreteCandidate, Set[str]) -> None
        self._candidate = candidate
        self._extras = extras

    @property
    def name(self):
        # type: () -> str
        return format_name(self._candidate.name, self._extras)

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self._candidate.version

    @property
    def link(self):
        # type: () -> Link
        return self._candidate.link

    def get_dependencies(self, make_req):
        # type: (RequirementProvider) -> Sequence[Requirement]
        return [
            make_req(str(r), self._candidate._ireq)
            for r in self._candidate._dist.requires(self._extras)
        ]


class ConcreteCandidate(Candidate):
    def __init__(self, ireq, dist):
        # type: (InstallRequirement, Distribution) -> None
        assert ireq.link is not None, "Candidate should be pinned"
        assert ireq.req is not None, "Un-specified requirement not allowed"
        assert ireq.req.url is not None, "Candidate should be pinned"
        self._ireq = ireq
        self._dist = dist

    @classmethod
    def from_abstract_dist(
        cls,
        adist,      # type: AbstractDistribution
        ireq,       # type: InstallRequirement
        options,    # type: ResolveOptions
    ):
        # type: (...) -> Optional[ConcreteCandidate]
        dist = adist.get_pkg_resources_distribution()
        try:
            _check_dist_requires_python(
                dist,
                options.python_version_info,
                options.ignore_requires_python,
            )
        except UnsupportedPythonVersion:
            return None
        return cls(ireq, dist)

    @property
    def name(self):
        # type: () -> str
        return canonicalize_name(self._ireq.req.name)

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self._dist.parsed_version

    @property
    def link(self):
        # type: () -> Link
        assert self._ireq.link is not None, "Candidate should be pinned"
        return self._ireq.link

    def get_dependencies(self, make_req):
        # type: (RequirementProvider) -> Sequence[Requirement]
        return [
            make_req(str(r), self._ireq)
            for r in self._dist.requires()
        ]


class RemoteCandidate(ConcreteCandidate):
    """Candidate pointing to a remote location.

    A remote location can be on-disk, but not installed into the environment.
    """


class EditableCandidate(ConcreteCandidate):
    """Candidate pointing to an editable source.
    """


class InstalledCandidate(ConcreteCandidate):
    """Candidate pointing to an installed dist/egg.
    """
