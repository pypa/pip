import logging

from pip._vendor.resolvelib.reporters import BaseReporter

logger = logging.getLogger(__name__)


class PipDebuggingReporter(BaseReporter):
    """A basic reporter that does a debug log for every event it sees."""

    def starting(self):
        logger.debug("Reporter.starting()")

    def starting_round(self, index):
        logger.debug("Reporter.starting_round(%r)", index)

    def ending_round(self, index, state):
        logger.debug("Reporter.ending_round(%r, state)", index)

    def ending(self, state):
        logger.debug("Reporter.ending(state)")

    def adding_requirement(self, requirement, parent):
        logger.debug("Reporter.adding_requirement(%r, %r)", requirement, parent)

    def backtracking(self, candidate):
        logger.debug("Reporter.backtracking(%r)", candidate)

    def pinning(self, candidate):
        logger.debug("Reporter.pinning(%r)", candidate)
