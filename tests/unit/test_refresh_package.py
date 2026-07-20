from optparse import Values

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS


class SimpleCommand(Command):
    def __init__(self) -> None:
        super().__init__("fake", "fake summary")

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.refresh_package())

    def run(self, options: Values, args: list[str]) -> int:
        self.options = options
        return SUCCESS


def test_canonicalization() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--refresh-package=Requests"])
    assert cmd.options.refresh_package == {"requests"}


def test_single_package() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--refresh-package=requests"])

    assert cmd.options.refresh_package == {"requests"}


def test_comma_separated_values() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--refresh-package=requests,urllib3,charset-normalizer"])

    assert cmd.options.refresh_package == {
        "requests",
        "urllib3",
        "charset-normalizer",
    }


def test_all() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--refresh-package=:all:"])

    assert cmd.options.refresh_package == {":all:"}


def test_none() -> None:
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--refresh-package=requests",
            "--refresh-package=:none:",
        ]
    )

    assert cmd.options.refresh_package == set()


def test_all_then_none() -> None:
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--refresh-package=:all:",
            "--refresh-package=:none:",
        ]
    )

    assert cmd.options.refresh_package == set()


def test_none_then_package() -> None:
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--refresh-package=:all:",
            "--refresh-package=:none:",
            "--refresh-package=requests",
        ]
    )

    assert cmd.options.refresh_package == {"requests"}


def test_all_discards_previous_values() -> None:
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--refresh-package=requests",
            "--refresh-package=:all:",
        ]
    )

    assert cmd.options.refresh_package == {":all:"}


def test_all_comma_separataed() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--refresh-package=requests,:all:,urllib3"])

    assert cmd.options.refresh_package == {":all:"}
