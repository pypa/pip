from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Sequence, Set
    from pip._vendor.packaging.version import _BaseVersion
    from pip._internal.models.link import Link
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


class ConcreteCandidate(Candidate):
    def get_dependencies(self):
        # type: () -> Sequence[Requirement]
        # TODO: Imeplement me.
        # Read the metadata and return requirements for each Requires-Dist.
        # This does not need to consider extras.
        raise NotImplementedError()


class NamedCandidate(ConcreteCandidate):
    def __init__(self, name, version, link):
        # type: (str, _BaseVersion, Link) -> None
        self._name = canonicalize_name(name)
        self._link = link
        self._version = version

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self._version

    @property
    def link(self):
        # type: () -> Link
        return self._link

    def same_as(self, other):
        # type: (Candidate) -> bool
        # The version check goes first because the resolver shouldn't need
        # to ask if the name does not match.
        return self.version == other.version and self.name == other.name


class DirectCandidate(ConcreteCandidate):
    """Candidate pointing to a direct URL.

    This resolves the ``version`` property lazily, avoid building the
    requirement unnecessarily.
    """
    def __init__(self, name, link):
        # type: (str, Link) -> None
        self._name = canonicalize_name(name)
        self._link = link
        self._version = None  # type: Optional[_BaseVersion]

    def same_as(self, other):
        # type: (Candidate) -> bool
        return self.link == other.link

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def link(self):
        # type: () -> Link
        return self._link

    @property
    def version(self):
        # type: () -> _BaseVersion
        if self._version is not None:
            return self._version
        # TODO: Fetch version lazily by fetching and building from source.
        raise NotImplementedError()


class EditableCandidate(DirectCandidate):
    def same_as(self, other):
        # type: (Candidate) -> bool
        return (
            isinstance(other, EditableCandidate) and
            super(EditableCandidate, self).__eq__(other)
        )


class ExtrasCandidate(Candidate):
    def __init__(self, candidate, extras):
        # type: (ConcreteCandidate, Set[str]) -> None
        self.candidate = candidate
        self.extras = extras

    def same_as(self, other):
        # type: (Candidate) -> bool
        return (
            isinstance(other, ExtrasCandidate) and
            self.candidate.same_as(other.candidate)
        )

    @property
    def name(self):
        # type: () -> str
        return format_name(self.candidate.name, self.extras)

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self.candidate.version

    @property
    def link(self):
        # type: () -> Link
        return self.candidate.link

    def get_dependencies(self):
        # type: () -> Sequence[Requirement]
        # TODO: Imeplement me.
        # Need to return a DirectRequirement containing the same candidate sans
        # extras, and Requires-Dist entries specified by one of the extras.
        raise NotImplementedError()
