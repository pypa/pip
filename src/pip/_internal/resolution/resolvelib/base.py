import abc
from typing import FrozenSet, Iterable, Optional, Tuple, Union

from pip._vendor.packaging.requirements import Requirement as PkgRequirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import LegacyVersion, Version

from pip._internal.models.link import Link, links_equivalent
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.hashes import Hashes

CandidateLookup = Tuple[Optional["Candidate"], Optional[InstallRequirement]]
CandidateVersion = Union[LegacyVersion, Version]


def format_name(project: str, extras: FrozenSet[str]) -> str:
    if not extras:
        return project
    canonical_extras = sorted(canonicalize_name(e) for e in extras)
    return "{}[{}]".format(project, ",".join(canonical_extras))


class Constraint:
    def __init__(
        self, specifier: SpecifierSet, hashes: Hashes, links: FrozenSet[Link]
    ) -> None:
        self.specifier = specifier
        self.hashes = hashes
        self.links = links

    @classmethod
    def empty(cls) -> "Constraint":
        return Constraint(SpecifierSet(), Hashes(), frozenset())

    @classmethod
    def from_ireq(cls, ireq: InstallRequirement) -> "Constraint":
        links = frozenset([ireq.link]) if ireq.link else frozenset()
        return Constraint(ireq.specifier, ireq.hashes(trust_internet=False), links)

    def __bool__(self) -> bool:
        return bool(self.specifier) or bool(self.hashes) or bool(self.links)

    def __and__(self, other: InstallRequirement) -> "Constraint":
        if not isinstance(other, InstallRequirement):
            return NotImplemented
        specifier = self.specifier & other.specifier
        hashes = self.hashes & other.hashes(trust_internet=False)
        links = self.links
        if other.link:
            links = links.union([other.link])
        return Constraint(specifier, hashes, links)

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        # Reject if there are any mismatched URL constraints on this package.
        if self.links and not all(_match_link(link, candidate) for link in self.links):
            return False
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class Requirement(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def project_name(self) -> NormalizedName:
        """The "project name" of a requirement.

        This is different from ``name`` if this requirement contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """

    @abc.abstractproperty
    def name(self) -> str:
        """The name identifying this requirement in the resolver.

        This is different from ``project_name`` if this requirement contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        return False

    @abc.abstractmethod
    def get_candidate_lookup(self) -> CandidateLookup:
        ...

    @abc.abstractmethod
    def format_for_error(self) -> str:
        ...

    @abc.abstractmethod
    def as_serializable_requirement(self) -> Optional[PkgRequirement]:
        ...


def _match_link(link: Link, candidate: "Candidate") -> bool:
    if candidate.source_link:
        return links_equivalent(link, candidate.source_link)
    return False


class Candidate(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def project_name(self) -> NormalizedName:
        """The "project name" of the candidate.

        This is different from ``name`` if this candidate contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """

    @abc.abstractproperty
    def name(self) -> str:
        """The name identifying this candidate in the resolver.

        This is different from ``project_name`` if this candidate contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """

    @abc.abstractproperty
    def version(self) -> CandidateVersion:
        ...

    @abc.abstractmethod
    def as_serializable_requirement(self) -> PkgRequirement:
        ...

    @abc.abstractproperty
    def is_installed(self) -> bool:
        ...

    @abc.abstractproperty
    def is_editable(self) -> bool:
        ...

    @abc.abstractproperty
    def source_link(self) -> Optional[Link]:
        ...

    @abc.abstractmethod
    def iter_dependencies(self, with_requires: bool) -> Iterable[Optional[Requirement]]:
        ...

    @abc.abstractmethod
    def get_install_requirement(self) -> Optional[InstallRequirement]:
        ...

    @abc.abstractmethod
    def format_for_error(self) -> str:
        ...
