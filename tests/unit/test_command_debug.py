from __future__ import annotations

import os

import pytest

from pip._internal.commands.debug import DebugCommand, ca_bundle_info
from pip._internal.configuration import Kind
from pip._internal.exceptions import CommandError

from tests.lib.configuration_helpers import ConfigurationMixin


class TestCABundleInfo(ConfigurationMixin):
    @pytest.mark.parametrize(
        "config, expected",
        [
            ({"global.cert": "/g"}, "global"),
            ({"install.cert": "/i"}, "install"),
            ({"global.cert": "/g", "install.cert": "/i"}, "install"),
        ],
    )
    def test_reports_configured_level(
        self,
        config: dict[str, str],
        expected: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for name in list(os.environ):
            if name.startswith("PIP_"):
                monkeypatch.delenv(name)
        self.patch_configuration(Kind.USER, config)
        self.configuration.load()
        assert ca_bundle_info(self.configuration) == expected


def test_debug_rejects_unexpected_arguments() -> None:
    command = DebugCommand(name="debug", summary="Display debug information.")
    options, args = command.parse_args(["unexpected"])
    with pytest.raises(CommandError, match="Too many arguments"):
        command.run(options, args)
