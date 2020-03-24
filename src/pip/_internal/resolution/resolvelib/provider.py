import functools
import sys

from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.resolvelib.providers import AbstractProvider

from pip._internal.utils.misc import normalize_version_info
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .requirements import RequiredPythonRequirement, make_requirement

if MYPY_CHECK_RUNNING:
    from typing import Any, Optional, Sequence, Tuple, Union

    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.resolution.base import InstallRequirementProvider

    from .base import Requirement, Candidate


class PipProvider(AbstractProvider):
    def __init__(
        self,
        finder,    # type: PackageFinder
        preparer,  # type: RequirementPreparer
        ignore_dependencies,  # type: bool
        ignore_requires_python,  # type: bool
        py_version_info,  # type: Optional[Tuple[int, ...]]
        make_install_req  # type: InstallRequirementProvider
    ):
        # type: (...) -> None
        self._finder = finder
        self._preparer = preparer
        self._ignore_dependencies = ignore_dependencies
        self._make_install_req = make_install_req

        if py_version_info is None:
            py_version_info = sys.version_info[:3]
        else:
            py_version_info = normalize_version_info(py_version_info)
        self._make_python_req = functools.partial(
            RequiredPythonRequirement,
            parse_version(".".join(str(c) for c in py_version_info)),
        )

    def make_requirement(self, ireq):
        # type: (InstallRequirement) -> Requirement
        return make_requirement(
            ireq,
            self._finder,
            self._preparer,
            self._make_install_req,
            self._make_python_req,
        )

    def get_install_requirement(self, c):
        # type: (Candidate) -> InstallRequirement

        # The base Candidate class does not have an _ireq attribute, so we
        # fetch it dynamically here, to satisfy mypy. In practice, though, we
        # only ever deal with LinkedCandidate objects at the moment, which do
        # have an _ireq attribute.  When we have a candidate type for installed
        # requirements we should probably review this.
        #
        # TODO: Longer term, make a proper interface for this on the candidate.
        return getattr(c, "_ireq", None)

    def identify(self, dependency):
        # type: (Union[Requirement, Candidate]) -> str
        return dependency.name

    def get_preference(
        self,
        resolution,  # type: Optional[Candidate]
        candidates,  # type: Sequence[Candidate]
        information  # type: Sequence[Tuple[Requirement, Candidate]]
    ):
        # type: (...) -> Any
        # Use the "usual" value for now
        return len(candidates)

    def find_matches(self, requirement):
        # type: (Requirement) -> Sequence[Candidate]
        return requirement.find_matches()

    def is_satisfied_by(self, requirement, candidate):
        # type: (Requirement, Candidate) -> bool
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate):
        # type: (Candidate) -> Sequence[Requirement]
        if self._ignore_dependencies:
            return []
        return [
            make_requirement(
                r,
                self._finder,
                self._preparer,
                self._make_install_req,
                self._make_python_req,
            )
            for r in candidate.get_dependencies()
        ]
