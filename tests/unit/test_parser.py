"""Tests for ConfigOptionParser.check_default behaviour."""

from __future__ import annotations

import logging
import optparse
from unittest.mock import patch

import pytest

from pip._internal.cli.parser import ConfigOptionParser


class TestCheckDefaultInvalidValue:
    """Invalid config values must not brick pip (issue #8671).

    check_default() used to call sys.exit(3) when a config file contained
    an invalid option value (e.g. ``use-feature = bad-value``).  This made
    pip completely unusable — even ``pip config unset`` would abort before
    doing anything useful.

    The fix: emit a warning and return None so pip continues normally.
    """

    def _make_parser(self) -> ConfigOptionParser:
        with patch("pip._internal.cli.parser.Configuration"):
            return ConfigOptionParser(name="install")

    def _make_option_with_choices(
        self, choices: list[str]
    ) -> optparse.Option:
        opt = optparse.Option(
            "--use-feature",
            dest="use_feature",
            choices=choices,
            action="store",
        )
        return opt

    def test_invalid_value_warns_and_returns_none(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An invalid config value must emit a warning and return None.

        Previously pip called sys.exit(3) here, making it completely
        unusable when a stale or unknown use-feature value was present.
        """
        parser = self._make_parser()
        option = self._make_option_with_choices(["fast-deps", "truststore"])

        with caplog.at_level(logging.WARNING, logger="pip._internal.cli.parser"):
            result = parser.check_default(option, "--use-feature", "bad-value")

        assert result is None
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING

    def test_valid_value_passes_through(self) -> None:
        """Valid config values must still work correctly."""
        parser = self._make_parser()
        option = self._make_option_with_choices(["fast-deps", "truststore"])

        result = parser.check_default(option, "--use-feature", "fast-deps")

        assert result == "fast-deps"
