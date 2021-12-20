import abc
from typing import TYPE_CHECKING, Callable, List, Optional, cast

from pip._vendor.packaging.utils import NormalizedName

from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet

if TYPE_CHECKING:
    from pip._vendor.resolvelib.resolvers import Result as RLResult

    from .resolvelib.base import Candidate, Requirement

    Result = RLResult[Requirement, Candidate, str]

InstallRequirementProvider = Callable[
    [str, Optional[InstallRequirement]], InstallRequirement
]


# Avoid conflicting with the PyPI package "Python".
REQUIRES_PYTHON_IDENTIFIER = cast(NormalizedName, "<Python from Requires-Python>")
# Avoid clashing with any package on PyPI, but remain parseable as a Requirement. This
# should only be used for .as_serializable_requirement().
REQUIRES_PYTHON_SERIALIZABLE_IDENTIFIER = cast(NormalizedName, "Requires-Python")


class RequirementSetWithCandidates(RequirementSet):
    def __init__(
        self,
        candidates: "Result",
        check_supported_wheels: bool = True,
    ) -> None:
        self.candidates = candidates
        super().__init__(check_supported_wheels=check_supported_wheels)


class BaseResolver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        ...

    @abc.abstractmethod
    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        ...
