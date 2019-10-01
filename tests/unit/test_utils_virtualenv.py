import site
import sys

import pytest

from pip._internal.utils import virtualenv


@pytest.mark.parametrize(
    "real_prefix, base_prefix, expected", [
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
def test_running_under_virtualenv(
        monkeypatch, real_prefix, base_prefix, expected,
):
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
    "running_under_virtualenv, no_global_file, expected", [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (True, True, True),
    ],
)
def test_virtualenv_no_global(
        monkeypatch, tmpdir,
        running_under_virtualenv, no_global_file, expected,
):
    monkeypatch.setattr(site, '__file__', tmpdir / 'site.py')
    monkeypatch.setattr(
        virtualenv, 'running_under_virtualenv',
        lambda: running_under_virtualenv,
    )
    if no_global_file:
        (tmpdir / 'no-global-site-packages.txt').touch()
    assert virtualenv.virtualenv_no_global() == expected
