from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .base import Candidate, format_name

if MYPY_CHECK_RUNNING:
    from typing import Any, Dict, Optional, Sequence, Set

    from pip._internal.models.link import Link
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.resolution.base import InstallRequirementProvider

    from pip._vendor.packaging.version import _BaseVersion
    from pip._vendor.pkg_resources import Distribution


_CANDIDATE_CACHE = {}  # type: Dict[Link, LinkCandidate]


def make_candidate(
    link,              # type: Link
    preparer,          # type: RequirementPreparer
    parent,            # type: InstallRequirement
    make_install_req,  # type: InstallRequirementProvider
    extras             # type: Set[str]
):
    # type: (...) -> Candidate
    if link not in _CANDIDATE_CACHE:
        _CANDIDATE_CACHE[link] = LinkCandidate(
            link,
            preparer,
            parent=parent,
            make_install_req=make_install_req
        )
    base = _CANDIDATE_CACHE[link]
    if extras:
        return ExtrasCandidate(base, extras)
    return base


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
        self._make_install_req = lambda spec: make_install_req(
            spec,
            self._ireq
        )

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
        return [self._make_install_req(str(r)) for r in self.dist.requires()]

    def get_install_requirement(self):
        # type: () -> Optional[InstallRequirement]
        return self._ireq


class ExtrasCandidate(LinkCandidate):
    """A candidate that has 'extras', indicating additional dependencies.

    Requirements can be for a project with dependencies, something like
    foo[extra].  The extras don't affect the project/version being installed
    directly, but indicate that we need additional dependencies. We model that
    by having an artificial ExtrasCandidate that wraps the "base" candidate.

    The ExtrasCandidate differs from the base in the following ways:

    1. It has a unique name, of the form foo[extra]. This causes the resolver
       to treat it as a separate node in the dependency graph.
    2. When we're getting the candidate's dependencies,
       a) We specify that we want the extra dependencies as well.
       b) We add a dependency on the base candidate (matching the name and
          version).  See below for why this is needed.
    3. We return None for the underlying InstallRequirement, as the base
       candidate will provide it, and we don't want to end up with duplicates.

    The dependency on the base candidate is needed so that the resolver can't
    decide that it should recommend foo[extra1] version 1.0 and foo[extra2]
    version 2.0. Having those candidates depend on foo=1.0 and foo=2.0
    respectively forces the resolver to recognise that this is a conflict.
    """
    def __init__(
        self,
        base,      # type: LinkCandidate
        extras,    # type: Set[str]
    ):
        # type: (...) -> None
        self.base = base
        self.extras = extras
        self.link = base.link

    @property
    def name(self):
        # type: () -> str
        """The normalised name of the project the candidate refers to"""
        return format_name(self.base.name, self.extras)

    @property
    def version(self):
        # type: () -> _BaseVersion
        return self.base.version

    def get_dependencies(self):
        # type: () -> Sequence[InstallRequirement]
        # TODO: We should probably warn if the user specifies an unsupported
        # extra. We can't do this in the constructor, as we don't know what
        # extras are valid until we prepare the candidate. Probably the best
        # approach would be to override the base class ``dist`` property, to
        # do an additional check of the extras, and if any are invalid, warn
        # and remove them from extras. This will be tricky to get right,
        # though, as modifying the extras changes the candidate's name and
        # hence identity, which isn't acceptable. So for now, we just ignore
        # unsupported extras here.

        # The user may have specified extras that the candidate doesn't
        # support. We ignore any unsupported extras here.
        valid_extras = self.extras.intersection(self.base.dist.extras)

        deps = [
            self.base._make_install_req(str(r))
            for r in self.base.dist.requires(valid_extras)
        ]
        # Add a dependency on the exact base.
        # (See note 2b in the class docstring)
        spec = "{}=={}".format(self.base.name, self.base.version)
        deps.append(self.base._make_install_req(spec))
        return deps

    def get_install_requirement(self):
        # type: () -> Optional[InstallRequirement]
        # We don't return anything here, because we always
        # depend on the base candidate, and we'll get the
        # install requirement from that.
        return None
