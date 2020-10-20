from collections import defaultdict
from logging import getLogger

from pip._vendor.resolvelib.reporters import BaseReporter

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import DefaultDict

    from .base import Candidate


logger = getLogger(__name__)


class PipReporter(BaseReporter):

    def __init__(self):
        # type: () -> None
        self.backtracks_by_package = defaultdict(int)  # type: DefaultDict[str, int]

        self._messages_at_backtrack = {
            8: (
                "pip is looking at multiple versions of this package to determine "
                "which version is compatible with other requirements. "
                "This could take a while."
            ),
            13: (
                "This is taking longer than usual. You might need to provide the "
                "dependency resolver with stricter constraints to reduce runtime."
                "If you want to abort this run, you can press Ctrl + C to do so."
            )
        }

    def backtracking(self, candidate):
        # type: (Candidate) -> None
        self.backtracks_by_package[candidate.name] += 1

        count = self.backtracks_by_package[candidate.name]
        if count not in self._messages_at_backtrack:
            return

        message = self._messages_at_backtrack[count]
        logger.info(message)
