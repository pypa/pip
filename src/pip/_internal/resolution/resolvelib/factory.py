from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import ExtrasCandidate, LinkCandidate
from .requirements import ExplicitRequirement, SpecifierRequirement

if MYPY_CHECK_RUNNING:
    from typing import Dict, Set

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.models.link import Link
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.resolution.base import InstallRequirementProvider

    from .base import Candidate, Requirement


class Factory(object):
    def __init__(
        self,
        finder,  # type: PackageFinder
        preparer,  # type: RequirementPreparer
        make_install_req,  # type: InstallRequirementProvider
    ):
        # type: (...) -> None
        self._finder = finder
        self._preparer = preparer
        self._make_install_req = make_install_req
        self._candidate_cache = {}  # type: Dict[Link, LinkCandidate]

    def make_candidate(
        self,
        link,    # type: Link
        extras,  # type: Set[str]
        parent,  # type: InstallRequirement
    ):
        # type: (...) -> Candidate
        if link not in self._candidate_cache:
            self._candidate_cache[link] = LinkCandidate(
                link,
                self._preparer,
                parent=parent,
                make_install_req=self._make_install_req
            )
        base = self._candidate_cache[link]
        if extras:
            return ExtrasCandidate(base, extras)
        return base

    def make_requirement(self, ireq):
        # type: (InstallRequirement) -> Requirement
        if ireq.link:
            cand = self.make_candidate(ireq.link, extras=set(), parent=ireq)
            return ExplicitRequirement(cand)
        else:
            return SpecifierRequirement(
                ireq,
                finder=self._finder,
                factory=self,
                make_install_req=self._make_install_req,
            )
