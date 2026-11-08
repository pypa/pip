from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from pip._internal.resolution.resolvelib.reporter import PipReporter


def _criterion() -> Mock:
    criterion = Mock()
    criterion.information = []
    return criterion


def _candidate(name: str = "django") -> Mock:
    candidate = Mock()
    candidate.name = name
    return candidate


def test_no_multiple_versions_message_on_first_rejection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    reporter = PipReporter()
    reporter.rejecting_candidate(_criterion(), _candidate())
    assert "looking at multiple versions" not in caplog.text


def test_multiple_versions_message_on_second_rejection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    reporter = PipReporter()
    reporter.rejecting_candidate(_criterion(), _candidate())
    reporter.rejecting_candidate(_criterion(), _candidate())
    assert "looking at multiple versions of django" in caplog.text
