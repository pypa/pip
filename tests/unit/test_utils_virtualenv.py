import logging
import site
import sys

import pytest

from pip._internal.utils import virtualenv


@pytest.mark.parametrize(
    "real_prefix, base_prefix, expected",
    [
        (None, None, False),  # Python 2 base interpreter
        (None, sys.prefix, False),  # Python 3 base interpreter
        (None, "not_sys_prefix", True),  # PEP405 venv
        (sys.prefix, None, True),  # Unknown case
        (sys.prefix, sys.prefix, True),  # Unknown case
        (sys.prefix, "not_sys_prefix", True),  # Unknown case
        ("not_sys_prefix", None, True),  # Python 2 virtualenv
        ("not_sys_prefix", sys.prefix, True),  # Python 3 virtualenv
        ("not_sys_prefix", "not_sys_prefix", True),  # Unknown case
    ],
)
def test_running_under_virtualenv(monkeypatch, real_prefix, base_prefix, expected):
    # Use raising=False to prevent AttributeError on missing attribute
    if real_prefix is None:
        monkeypatch.delattr(sys, "real_prefix", raising=False)
    else:
        monkeypatch.setattr(sys, "real_prefix", real_prefix, raising=False)
    if base_prefix is None:
        monkeypatch.delattr(sys, "base_prefix", raising=False)
    else:
        monkeypatch.setattr(sys, "base_prefix", base_prefix, raising=False)
    assert virtualenv.running_under_virtualenv() == expected


@pytest.mark.parametrize(
    "under_virtualenv, no_global_file, expected",
    [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (True, True, True),
    ],
)
def test_virtualenv_no_global_with_regular_virtualenv(
    monkeypatch,
    tmpdir,
    under_virtualenv,
    no_global_file,
    expected,
):
    monkeypatch.setattr(virtualenv, "_running_under_venv", lambda: False)

    monkeypatch.setattr(site, "__file__", tmpdir / "site.py")
    monkeypatch.setattr(
        virtualenv,
        "_running_under_regular_virtualenv",
        lambda: under_virtualenv,
    )
    if no_global_file:
        (tmpdir / "no-global-site-packages.txt").touch()

    assert virtualenv.virtualenv_no_global() == expected


@pytest.mark.parametrize(
    "pyvenv_cfg_lines, under_venv, expected, expect_warning",
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
    monkeypatch,
    caplog,
    pyvenv_cfg_lines,
    under_venv,
    expected,
    expect_warning,
):
    monkeypatch.setattr(virtualenv, "_running_under_regular_virtualenv", lambda: False)
    monkeypatch.setattr(virtualenv, "_get_pyvenv_cfg_lines", lambda: pyvenv_cfg_lines)
    monkeypatch.setattr(virtualenv, "_running_under_venv", lambda: under_venv)

    with caplog.at_level(logging.WARNING):
        assert virtualenv.virtualenv_no_global() == expected

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
    monkeypatch,
    tmpdir,
    contents,
    expected,
):
    monkeypatch.setattr(sys, "prefix", str(tmpdir))
    if contents is not None:
        tmpdir.joinpath("pyvenv.cfg").write_text(contents)

    assert virtualenv._get_pyvenv_cfg_lines() == expected
