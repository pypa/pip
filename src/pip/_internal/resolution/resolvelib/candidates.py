from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import Candidate

if MYPY_CHECK_RUNNING:
    from typing import Any, Dict, Optional, Sequence

    from pip._internal.models.link import Link
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.resolution.base import InstallRequirementProvider

    from pip._vendor.packaging.version import _BaseVersion
    from pip._vendor.pkg_resources import Distribution


_CANDIDATE_CACHE = {}  # type: Dict[Link, Candidate]


def make_candidate(
    link,             # type: Link
    preparer,         # type: RequirementPreparer
    parent,           # type: InstallRequirement
    make_install_req  # type: InstallRequirementProvider
):
    # type: (...) -> Candidate
    if link not in _CANDIDATE_CACHE:
        _CANDIDATE_CACHE[link] = LinkCandidate(
            link,
            preparer,
            parent=parent,
            make_install_req=make_install_req
        )
    return _CANDIDATE_CACHE[link]


def make_install_req_from_link(link, parent):
    # type: (Link, InstallRequirement) -> InstallRequirement
    # TODO: Do we need to support editables?
    return install_req_from_line(
        link.url,
        comes_from=parent.comes_from,
        use_pep517=parent.use_pep517,
        isolated=parent.isolated,
        wheel_cache=parent._wheel_cache,
        constraint=parent.constraint,
        options=dict(
            install_options=parent.install_options,
            global_options=parent.global_options,
            hashes=parent.hash_options
        ),
    )


class LinkCandidate(Candidate):
    def __init__(
        self,
        link,      # type: Link
        preparer,  # type: RequirementPreparer
        parent,    # type: InstallRequirement
        make_install_req,  # type: InstallRequirementProvider
    ):
        # type: (...) -> None
        self.link = link
        self._preparer = preparer
        self._ireq = make_install_req_from_link(link, parent)
        self._make_install_req = make_install_req

        self._name = None  # type: Optional[str]
        self._version = None  # type: Optional[_BaseVersion]
        self._dist = None  # type: Optional[Distribution]

    def __eq__(self, other):
        # type: (Any) -> bool
        if isinstance(other, self.__class__):
            return self.link == other.link
        return False

    # Needed for Python 2, which does not implement this by default
    def __ne__(self, other):
        # type: (Any) -> bool
        return not self.__eq__(other)

    @property
    def name(self):
        # type: () -> str
        """The normalised name of the project the candidate refers to"""
        if self._name is None:
            self._name = canonicalize_name(self.dist.project_name)
        return self._name

    @property
    def version(self):
        # type: () -> _BaseVersion
        if self._version is None:
            self._version = self.dist.parsed_version
        return self._version

    @property
    def dist(self):
        # type: () -> Distribution
        if self._dist is None:
            abstract_dist = self._preparer.prepare_linked_requirement(
                self._ireq
            )
            self._dist = abstract_dist.get_pkg_resources_distribution()
            # TODO: Only InstalledDistribution can return None here :-(
            assert self._dist is not None
            # These should be "proper" errors, not just asserts, as they
            # can result from user errors like a requirement "foo @ URL"
            # when the project at URL has a name of "bar" in its metadata.
            assert (self._name is None or
                    self._name == canonicalize_name(self._dist.project_name))
            assert (self._version is None or
                    self._version == self.dist.parsed_version)
        return self._dist

    def get_dependencies(self):
        # type: () -> Sequence[InstallRequirement]
        return [
            self._make_install_req(str(r), self._ireq)
            for r in self.dist.requires()
        ]
