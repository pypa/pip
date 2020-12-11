from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, List

    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.req.req_set import RequirementSet

    InstallRequirementProvider = Callable[
        [str, InstallRequirement], InstallRequirement
    ]


class BaseResolver(object):
    def resolve(self, root_reqs, check_supported_wheels, should_backtrack):
        # type: (List[InstallRequirement], bool, bool) -> RequirementSet
        raise NotImplementedError()

    def get_installation_order(self, req_set):
        # type: (RequirementSet) -> List[InstallRequirement]
        raise NotImplementedError()
