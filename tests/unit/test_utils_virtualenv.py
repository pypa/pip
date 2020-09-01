import logging
import sys

import pytest

from pip._internal.utils import virtualenv


@pytest.mark.parametrize(
    "pyvenv_cfg_lines, under_venv, expected, expect_warning", [
        (None, False, True, True),
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
    monkeypatch.setattr(
        virtualenv, '_running_under_regular_virtualenv', lambda: False
    )
    monkeypatch.setattr(
        virtualenv, '_get_pyvenv_cfg_lines', lambda: pyvenv_cfg_lines
    )
    monkeypatch.setattr(virtualenv, '_running_under_venv', lambda: under_venv)

    with caplog.at_level(logging.WARNING):
        assert virtualenv.virtualenv_no_global() == expected

    if expect_warning:
        assert caplog.records

        # Check for basic information
        message = caplog.records[-1].getMessage().lower()
        assert "could not access 'pyvenv.cfg'" in message
        assert "assuming global site-packages is not accessible" in message


@pytest.mark.parametrize(
    "contents, expected", [
        (None, None),
        ("", []),
        ("a = b\nc = d\n", ["a = b", "c = d"]),
        ("a = b\nc = d", ["a = b", "c = d"]),  # no trailing newlines
    ]
)
def test_get_pyvenv_cfg_lines_for_pep_405_virtual_environment(
    monkeypatch,
    tmpdir,
    contents,
    expected,
):
    monkeypatch.setattr(sys, 'prefix', str(tmpdir))
    if contents is not None:
        tmpdir.joinpath('pyvenv.cfg').write_text(contents)

    assert virtualenv._get_pyvenv_cfg_lines() == expected
