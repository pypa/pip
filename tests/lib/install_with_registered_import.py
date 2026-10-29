"""Keep a registered dependency usable after its source file is replaced."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pip

if TYPE_CHECKING:
    from pip._internal.metadata import BaseEnvironment


def main() -> int:
    # Registration must work before importing pip's command internals.
    pip._EAGER_IMPORTS.add("pip_eager_owner")

    from pip._internal.cli.main import main as pip_main
    from pip._internal.commands import install

    original = install.get_environment

    def get_environment(locations: list[str] | None) -> BaseEnvironment:
        assert sys.modules["pip_eager_owner"].value() == "before installation"
        return original(locations)

    with patch.object(install, "get_environment", get_environment):
        return pip_main(["install", "--no-index", sys.argv[1]])


if __name__ == "__main__":
    sys.exit(main())
