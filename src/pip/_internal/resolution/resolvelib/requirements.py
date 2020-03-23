from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import Requirement
from .candidates import make_candidate

if MYPY_CHECK_RUNNING:
    from typing import Sequence

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.resolution.base import InstallRequirementProvider

    from .base import Candidate


def make_requirement(
    ireq,      # type: InstallRequirement
    finder,    # type: PackageFinder
    preparer,  # type: RequirementPreparer
    make_install_req  # type: InstallRequirementProvider
):
    # type: (...) -> Requirement
    if ireq.link:
        candidate = make_candidate(
            ireq.link,
            preparer,
            ireq,
            make_install_req
        )
        return ExplicitRequirement(candidate)
    else:
        return SpecifierRequirement(
            ireq,
            finder,
            preparer,
            make_install_req
        )


class ExplicitRequirement(Requirement):
    def __init__(self, candidate):
        # type: (Candidate) -> None
        self.candidate = candidate

    @property
    def name(self):
        # type: () -> str
        # No need to canonicalise - the candidate did this
        return self.candidate.name

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        return [self.candidate]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate == self.candidate


class SpecifierRequirement(Requirement):
    def __init__(
        self,
        ireq,      # type: InstallRequirement
        finder,    # type: PackageFinder
        preparer,  # type:RequirementPreparer
        make_install_req  # type: InstallRequirementProvider
    ):
        # type: (...) -> None
        assert ireq.link is None, "This is a link, not a specifier"
        assert not ireq.req.extras, "Extras not yet supported"
        self._ireq = ireq
        self._finder = finder
        self._preparer = preparer
        self._make_install_req = make_install_req

    @property
    def name(self):
        # type: () -> str
        canonical_name = canonicalize_name(self._ireq.req.name)
        return canonical_name

    def find_matches(self):
        # type: () -> Sequence[Candidate]
        found = self._finder.find_best_candidate(
            project_name=self._ireq.req.name,
            specifier=self._ireq.req.specifier,
            hashes=self._ireq.hashes(trust_internet=False),
        )
        return [
            make_candidate(
                ican.link,
                self._preparer,
                self._ireq,
                self._make_install_req
            )
            for ican in found.iter_applicable()
        ]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        assert candidate.name == self.name, \
            "Internal issue: Candidate is not for this requirement " \
            " {} vs {}".format(candidate.name, self.name)
        return candidate.version in self._ireq.req.specifier
