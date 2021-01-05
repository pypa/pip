from collections import defaultdict
from logging import getLogger

from pip._vendor.resolvelib.reporters import BaseReporter

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, DefaultDict

    from .base import Candidate, Requirement


logger = getLogger(__name__)


class _BasePipReporter(BaseReporter):
    def __init__(self, resolver_progress_path):
        # type: (str) -> None
        super().__init__()
        self._resolver_progress_path = resolver_progress_path
        self._indent = 0

    def backtracking(self, candidate):
        self._indent -= 1
        with open(self._resolver_progress_path, "a") as f:
            f.write("{}Back {}".format(" " * self._indent, candidate))

    def pinning(self, candidate):
        with open(self._resolver_progress_path, "a") as f:
            f.write("{}Pin  {}".format(" " * self._indent, candidate))
        self._indent += 1


class PipReporter(_BasePipReporter):

    def __init__(self, resolver_progress_path):
        # type: (str) -> None
        super().__init__(resolver_progress_path)
        self.backtracks_by_package = defaultdict(int)  # type: DefaultDict[str, int]

        self._messages_at_backtrack = {
            1: (
                "pip is looking at multiple versions of {package_name} to "
                "determine which version is compatible with other "
                "requirements. This could take a while."
            ),
            8: (
                "pip is looking at multiple versions of {package_name} to "
                "determine which version is compatible with other "
                "requirements. This could take a while."
            ),
            13: (
                "This is taking longer than usual. You might need to provide "
                "the dependency resolver with stricter constraints to reduce "
                "runtime. If you want to abort this run, you can press "
                "Ctrl + C to do so. To improve how pip performs, tell us what "
                "happened here: https://pip.pypa.io/surveys/backtracking"
            )
        }

    def backtracking(self, candidate):
        # type: (Candidate) -> None
        super().backtracking(candidate)
        self.backtracks_by_package[candidate.name] += 1

        count = self.backtracks_by_package[candidate.name]
        if count not in self._messages_at_backtrack:
            return

        message = self._messages_at_backtrack[count]
        logger.info("INFO: %s", message.format(package_name=candidate.name))


class PipDebuggingReporter(_BasePipReporter):
    """A reporter that does an info log for every event it sees."""

    def starting(self):
        # type: () -> None
        logger.info("Reporter.starting()")

    def starting_round(self, index):
        # type: (int) -> None
        logger.info("Reporter.starting_round(%r)", index)

    def ending_round(self, index, state):
        # type: (int, Any) -> None
        logger.info("Reporter.ending_round(%r, state)", index)

    def ending(self, state):
        # type: (Any) -> None
        logger.info("Reporter.ending(%r)", state)

    def adding_requirement(self, requirement, parent):
        # type: (Requirement, Candidate) -> None
        logger.info("Reporter.adding_requirement(%r, %r)", requirement, parent)

    def backtracking(self, candidate):
        # type: (Candidate) -> None
        super().backtracking(candidate)
        logger.info("Reporter.backtracking(%r)", candidate)

    def pinning(self, candidate):
        # type: (Candidate) -> None
        super().pinning(candidate)
        logger.info("Reporter.pinning(%r)", candidate)
