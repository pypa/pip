from pip._vendor.packaging.specifiers import SpecifierSet

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Set, Union
    from pip._vendor.packaging.version import _BaseVersion
    from pip._internal.models.link import Link


class DirectCandidate(object):
    """Candidate pointing to a direct URL.

    This is used instead of ``InstallationCandidate``to resolve the
    ``version`` property lazily, avoid building the requirement unnecessarily.
    """
    def __init__(self, name, link):
        # type: (str, Link) -> None
        self.name = name
        self.link = link
        self._version = None  # type: Optional[_BaseVersion]

    @property
    def version(self):
        # type: () -> _BaseVersion
        if self._version is not None:
            return self._version
        # TODO: Fetch version lazily by fetching and building from source.
        raise NotImplementedError()


class ExtrasCandidate(object):
    """Wrap a candidate with extras information.

    This class is used fpr a requirement's candidates when it requests extras,
    so we can later find extra dependencies with this information.
    """
    def __init__(
        self,
        candidate,  # type: Union[DirectCandidate, InstallationCandidate]
        extras,     # type: Set[str]
    ):
        # type: (...) -> None
        self.candidate = candidate
        self.extras = extras

    @property
    def name(self):
        # type: () -> str
        extras = sorted(self.extras)
        return "{}[{}]".format(self.candidate.name, ",".join(extras))

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self.candidate.version


class SingleCandidateRequirement(object):
    """A "simulated" requirement that holds only one candidate.

    This type is used as the requirement of an `ExtrasCandidate`, so we can
    skip finding candidates when resolving it later.
    """
    def __init__(self, candidate):
        # type: (ExtrasCandidate) -> None
        self.candidate = candidate.candidate

    @property
    def name(self):
        # type: () -> str
        return self.candidate.name

    @property
    def specifier(self):
        # type: () -> SpecifierSet
        return SpecifierSet("=={}".format(self.candidate.version))
