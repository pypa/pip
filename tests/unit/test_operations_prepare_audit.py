from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any

import pytest

from pip import __version__ as pip_version
from pip._internal.operations import prepare as prepare_module


class FakeBuildTracker:
    @contextmanager
    def track(self, req: Any, tracker_id: str) -> Any:
        yield


class FakeDistribution:
    build_tracker_id = None

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def get_metadata_distribution(self) -> object:
        self.calls.append("metadata")
        return object()


def test_prepare_distribution_emits_install_audit_event(monkeypatch: Any) -> None:
    calls: list[str] = []
    req = object()

    def audit_hook(event: str, args: tuple[object, ...]) -> None:
        if event == "pip.install" and args == (pip_version, req):
            calls.append("audit")

    def fake_make_distribution(req_arg: object) -> FakeDistribution:
        assert req_arg is req
        calls.append("distribution")
        return FakeDistribution(calls)

    sys.addaudithook(audit_hook)
    monkeypatch.setattr(
        prepare_module,
        "make_distribution_for_install_requirement",
        fake_make_distribution,
    )

    prepare_module._get_prepared_distribution(
        req, FakeBuildTracker(), object(), "off", False, True
    )

    assert calls == ["audit", "distribution", "metadata"]


def test_prepare_distribution_can_be_blocked_by_audit_hook() -> None:
    req = object()

    def audit_hook(event: str, args: tuple[object, ...]) -> None:
        if event == "pip.install" and args == (pip_version, req):
            raise RuntimeError("blocked by audit hook")

    sys.addaudithook(audit_hook)

    with pytest.raises(RuntimeError, match="blocked by audit hook"):
        prepare_module._get_prepared_distribution(
            req, FakeBuildTracker(), object(), "off", False, True
        )
