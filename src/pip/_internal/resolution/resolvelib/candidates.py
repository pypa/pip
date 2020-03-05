from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Sequence, Set
    from pip._vendor.packaging.version import _BaseVersion
    from pip._internal.models.link import Link
    from pip._internal.req.req_install import InstallRequirement
    from .requirements import Requirement


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

    def same_as(self, other):
        # type: (Candidate) -> bool
        return False

    def get_dependencies(self):
        # type: () -> Sequence[Requirement]
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


class ConcreteCandidate(Candidate):
    def __init__(self, ireq, version):
        # type: (InstallRequirement, _BaseVersion) -> None
        assert ireq.link is not None, "Candidate should be pinned"
        assert ireq.req is not None, "Un-prepared requirement not allowed"
        assert ireq.req.url is not None, "Candidate should be pinned"
        self._ireq = ireq
        self._version = version

    @property
    def name(self):
        # type: () -> str
        return canonicalize_name(self._ireq.req.name)

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self._version

    @property
    def link(self):
        # type: () -> Link
        assert self._ireq.link is not None, "Candidate should be pinned"
        return self._ireq.link


class RemoteCandidate(ConcreteCandidate):
    """Candidate pointing to a remote location.
    """


class EditableCandidate(ConcreteCandidate):
    """Candidate pointing to an editable source.
    """


class InstalledCandidate(ConcreteCandidate):
    """Candidate pointing to an installed dist/egg.
    """
