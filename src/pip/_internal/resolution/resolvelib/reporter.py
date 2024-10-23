from collections import defaultdict
from logging import getLogger
from typing import Any, DefaultDict

from pip._vendor.resolvelib.reporters import BaseReporter

from .base import Candidate, Requirement

logger = getLogger(__name__)


class PipReporter(BaseReporter):
    def adding_requirement(self, requirement: Requirement, parent: Requirement) -> None:
        if parent:
            logger.info("Adding requirement %s (from %s)", requirement, parent)
        else:
            logger.info("Adding requirement %s", requirement)

    def pinning(self, candidate: Candidate) -> None:
        logger.info("Pinning %s %s", candidate.name, candidate.version)

    def rejecting_candidate(self, criterion: Any, candidate: Candidate) -> None:
        msg = f"Rejecting {candidate.name} {candidate.version}, due to conflict:"
        for req_info in criterion.information:
            req, parent = req_info.requirement, req_info.parent
            # Inspired by Factory.get_installation_error
            msg += "\n    "
            if parent:
                msg += f"{parent.name} {parent.version} depends on "
            else:
                msg += "The user requested "
            msg += req.format_for_error()
        logger.info(msg)


class PipDebuggingReporter(BaseReporter):
    """A reporter that does an info log for every event it sees."""

    def starting(self) -> None:
        logger.info("Reporter.starting()")

    def starting_round(self, index: int) -> None:
        logger.info("Reporter.starting_round(%r)", index)

    def ending_round(self, index: int, state: Any) -> None:
        logger.info("Reporter.ending_round(%r, state)", index)
        logger.debug("Reporter.ending_round(%r, %r)", index, state)

    def ending(self, state: Any) -> None:
        logger.info("Reporter.ending(%r)", state)

    def adding_requirement(self, requirement: Requirement, parent: Candidate) -> None:
        logger.info("Reporter.adding_requirement(%r, %r)", requirement, parent)

    def rejecting_candidate(self, criterion: Any, candidate: Candidate) -> None:
        logger.info("Reporter.rejecting_candidate(%r, %r)", criterion, candidate)

    def pinning(self, candidate: Candidate) -> None:
        logger.info("Reporter.pinning(%r)", candidate)
