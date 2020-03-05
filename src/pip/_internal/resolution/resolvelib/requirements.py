import collections

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import (
    EditableCandidate,
    ExtrasCandidate,
    InstalledCandidate,
    RemoteCandidate,
    format_name,
)

if MYPY_CHECK_RUNNING:
    from typing import Optional, Sequence

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.models.candidate import InstallationCandidate
    from pip._internal.models.link import Link
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement

    from .candidates import Candidate, ConcreteCandidate


ResolveOptions = collections.namedtuple(
    "ResolveOptions",
    [
        # For checking whether a package is installed.
        "use_user_site",

        # For checking whether a dist is compatible.
        "python_version_info",
        "ignore_requires_python",
    ],
)


def _clone_install_requirement(ireq, link):
    # type: (InstallRequirement, Link) -> InstallRequirement
    return InstallRequirement(
        req=ireq.req,
        comes_from=ireq.comes_from,
        source_dir=ireq.source_dir,
        editable=ireq.editable,
        link=link,  # Link populated here (instead of cloning).
        markers=ireq.markers,
        use_pep517=ireq.use_pep517,
        isolated=ireq.isolated,
        install_options=ireq.install_options,
        global_options=ireq.global_options,
        hash_options=ireq.hash_options,
        # Do not perform cache lookup. `is_satisfied_by` may need the remote
        # link to check whether another requirement matches.
        # TODO: Do wheel cache lookup **after resolution**.
        wheel_cache=None,
        constraint=ireq.constraint,
        extras=ireq.extras,
    )


def _prepare_as_candidate(
    ireq,       # type: InstallRequirement
    ican,       # type: InstallationCandidate
    preparer,   # type: RequirementPreparer
    options,    # type: ResolveOptions
):
    # type: (...) -> Optional[ConcreteCandidate]
    if ireq.editable:
        dist = preparer.prepare_editable_requirement(ireq)
        return EditableCandidate.from_abstract_dist(dist, ireq, options)

    ireq.satisfied_by is None
    ireq.check_if_exists(use_user_site=options.use_user_site)

    # TODO: Do not use installed requirement under certain cercumstances.
    use_installed = (
        ireq.satisfied_by and
        ireq.satisfied_by.parsed_version == ican.version
    )

    if not use_installed:
        dist = preparer.prepare_linked_requirement(ireq)
        return RemoteCandidate.from_abstract_dist(dist, ireq, options)

    skip_reason = "installed"
    dist = preparer.prepare_installed_requirement(ireq, skip_reason)
    return InstalledCandidate.from_abstract_dist(dist, ireq, options)


def _pin_as_candidate(
    ireq,       # type: InstallRequirement
    ican,       # type: InstallationCandidate
    preparer,   # type: RequirementPreparer
    options,    # type: ResolveOptions
):
    # type: (...) -> Optional[Candidate]
    ireq = _clone_install_requirement(ireq, ican.link)
    candidate = _prepare_as_candidate(ireq, ican, preparer, options)
    if not candidate:
        return None
    if not ireq.req.extras:
        return candidate
    return ExtrasCandidate(candidate, ireq.req.extras)


class Requirement(object):
    @property
    def name(self):
        # type: () -> str
        raise NotImplementedError("Subclass should override")

    def find_matches(
        self,
        finder,     # type: PackageFinder
        preparer,   # type: RequirementPreparer
        options,    # type: ResolveOptions
    ):
        # type: (...) -> Sequence[Candidate]
        raise NotImplementedError("Subclass should override")

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return False


class DirectRequirement(Requirement):
    def __init__(self, candidate):
        # type: (Candidate) -> None
        self._candidate = candidate

    @property
    def name(self):
        # type: () -> str
        return self._candidate.name

    def find_matches(
        self,
        finder,     # type: PackageFinder
        preparer,   # type: RequirementPreparer
        options,    # type: ResolveOptions
    ):
        # type: (...) -> Sequence[Candidate]
        return [self._candidate]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate.link == self._candidate.link


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
        preparer,   # type: RequirementPreparer
        options,    # type: ResolveOptions
    ):
        # type: (...) -> Sequence[Candidate]
        found = finder.find_best_candidate(
            project_name=self._ireq.req.name,
            specifier=self._ireq.req.specifier,
            hashes=self._ireq.hashes(trust_internet=False),
        )
        candidates = (
            _pin_as_candidate(self._ireq, ican, preparer, options)
            for ican in found.iter_applicable()
        )
        return [c for c in candidates if c]

    def is_satisfied_by(self, candidate):
        # type: (Candidate) -> bool
        return candidate.version in self._ireq.req.specifier
