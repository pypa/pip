from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from pip._internal.utils import virtualenv


@pytest.mark.parametrize(
    "base_prefix, expected",
    [
        (None, False),  # base_prefix missing, falls back to sys.prefix
        (sys.prefix, False),  # base interpreter
        ("not_sys_prefix", True),  # PEP 405 venv
    ],
)
def test_running_under_virtualenv(
    monkeypatch: pytest.MonkeyPatch,
    base_prefix: str | None,
    expected: bool,
) -> None:
    # Use raising=False to prevent AttributeError on missing attribute
    if base_prefix is None:
        monkeypatch.delattr(sys, "base_prefix", raising=False)
    else:
        monkeypatch.setattr(sys, "base_prefix", base_prefix, raising=False)
    assert virtualenv.running_under_virtualenv() == expected


@pytest.mark.parametrize(
    "pyvenv_cfg_lines, under_venv, expect_no_global, expect_warning",
    [
        (None, False, False, False),
        (None, True, True, True),  # this has a warning.
        (
            [
                "home = <we do not care>",
                "include-system-site-packages = true",
                "version = <we do not care>",
            ],
            True,
            False,
            False,
        ),
        (
            [
                "home = <we do not care>",
                "include-system-site-packages = false",
                "version = <we do not care>",
            ],
            True,
            True,
            False,
        ),
    ],
)
def test_virtualenv_no_global_with_pep_405_virtual_environment(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    pyvenv_cfg_lines: list[str] | None,
    under_venv: bool,
    expect_no_global: bool,
    expect_warning: bool,
) -> None:
    monkeypatch.setattr(virtualenv, "_get_pyvenv_cfg_lines", lambda: pyvenv_cfg_lines)
    monkeypatch.setattr(virtualenv, "running_under_virtualenv", lambda: under_venv)

    with caplog.at_level(logging.WARNING):
        assert virtualenv.virtualenv_no_global() == expect_no_global

    if expect_warning:
        assert caplog.records

        # Check for basic information
        message = caplog.records[-1].getMessage().lower()
        assert "could not access 'pyvenv.cfg'" in message
        assert "assuming global site-packages is not accessible" in message


@pytest.mark.parametrize(
    "contents, expected",
    [
        (None, None),
        ("", []),
        ("a = b\nc = d\n", ["a = b", "c = d"]),
        ("a = b\nc = d", ["a = b", "c = d"]),  # no trailing newlines
    ],
)
def test_get_pyvenv_cfg_lines_for_pep_405_virtual_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmpdir: Path,
    contents: str | None,
    expected: list[str] | None,
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmpdir))
    if contents is not None:
        tmpdir.joinpath("pyvenv.cfg").write_text(contents)

    assert virtualenv._get_pyvenv_cfg_lines() == expected
