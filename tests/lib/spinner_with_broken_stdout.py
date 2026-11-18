"""Exercise command-level pipe handling after an animated spinner has started."""

import sys
from optparse import Values

from pip._internal.cli.base_command import Command
from pip._internal.cli.spinners import open_spinner


class SpinnerCommand(Command):
    ignore_require_venv = True

    def add_options(self) -> None:
        pass

    def run(self, options: Values, args: list[str]) -> int:
        with open_spinner("working"):
            # The parent closes stdout before allowing the operation to finish.
            sys.stdin.read(1)
        return 0


if __name__ == "__main__":
    sys.exit(SpinnerCommand("spinner-probe", "spinner-probe").main([]))
