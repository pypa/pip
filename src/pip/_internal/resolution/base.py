from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional

from pip._internal.req.req_install import InstallRequirement

if TYPE_CHECKING:
    from pip._internal.req.req_set import RequirementSet

InstallRequirementProvider = Callable[
    [str, Optional[InstallRequirement]], InstallRequirement
]


class BaseResolver:
    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        raise NotImplementedError()

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        raise NotImplementedError()
