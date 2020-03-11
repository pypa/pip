from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import Candidate, Requirement, format_name

if MYPY_CHECK_RUNNING:
    from typing import (Optional, Sequence)

    from pip._vendor.packaging.version import _BaseVersion

    from pip._internal.index.package_finder import PackageFinder


def make_requirement(install_req):
    # type: (InstallRequirement) -> Requirement
    if install_req.link:
        if install_req.req and install_req.req.name:
            return NamedRequirement(install_req)
        else:
            return UnnamedRequirement(install_req)
    else:
        return VersionedRequirement(install_req)


class UnnamedRequirement(Requirement):
    def __init__(self, req):
        # type: (InstallRequirement) -> None
        self._ireq = req
        self._candidate = None  # type: Optional[Candidate]

    @property
    def name(self):
        # type: () -> str
        assert self._ireq.req is None or self._ireq.name is None, \
            "Unnamed requirement has a name"
        # TODO: Get the candidate and use its name...
        return ""

    def _get_candidate(self):
        # type: () -> Candidate
        if self._candidate is None:
            self._candidate = Candidate()
        return self._candidate

    def find_matches(
        self,
        finder,     # type: PackageFinder
    ):
        # type: (...) -> Sequence[Candidate]
        return [self._get_candidate()]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate is self._get_candidate()


class NamedRequirement(Requirement):
    def __init__(self, req):
        # type: (InstallRequirement) -> None
        self._ireq = req
        self._candidate = None  # type: Optional[Candidate]

    @property
    def name(self):
        # type: () -> str
        assert self._ireq.req.name is not None, "Named requirement has no name"
        canonical_name = canonicalize_name(self._ireq.req.name)
        return format_name(canonical_name, self._ireq.req.extras)

    def _get_candidate(self):
        # type: () -> Candidate
        if self._candidate is None:
            self._candidate = Candidate()
        return self._candidate

    def find_matches(
        self,
        finder,     # type: PackageFinder
    ):
        # type: (...) -> Sequence[Candidate]
        return [self._get_candidate()]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate is self._get_candidate()


# TODO: This is temporary, to make the tests pass
class DummyCandidate(Candidate):
    def __init__(self, name, version):
        # type: (str, _BaseVersion) -> None
        self._name = name
        self._version = version

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self._version


class VersionedRequirement(Requirement):
    def __init__(self, ireq):
        # type: (InstallRequirement) -> None
        assert ireq.req is not None, "Un-specified requirement not allowed"
        assert ireq.req.url is None, "Direct reference not allowed"
        self._ireq = ireq

    @property
    def name(self):
        # type: () -> str
        canonical_name = canonicalize_name(self._ireq.req.name)
        return format_name(canonical_name, self._ireq.req.extras)

    def find_matches(
        self,
        finder,     # type: PackageFinder
    ):
        # type: (...) -> Sequence[Candidate]
        found = finder.find_best_candidate(
            project_name=self._ireq.req.name,
            specifier=self._ireq.req.specifier,
            hashes=self._ireq.hashes(trust_internet=False),
        )
        return [
            DummyCandidate(ican.name, ican.version)
            for ican in found.iter_applicable()
        ]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        # TODO: Should check name matches as well. Defer this
        #       until we have the proper Candidate object, and
        #       no longer have to deal with unnmed requirements...
        return candidate.version in self._ireq.req.specifier
