from __future__ import annotations

from optparse import Values

import pytest

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.models.release_control import ReleaseControl


class SimpleCommand(Command):
    def __init__(self) -> None:
        super().__init__("fake", "fake summary")

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.all_releases())
        self.cmd_opts.add_option(cmdoptions.only_final())

    def run(self, options: Values, args: list[str]) -> int:
        self.options = options
        return SUCCESS


def test_all_releases_overrides() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--only-final=:all:", "--all-releases=fred"])
    release_control = ReleaseControl({"fred"}, {":all:"})
    assert cmd.options.release_control == release_control


def test_only_final_overrides() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=:all:", "--only-final=fred"])
    release_control = ReleaseControl({":all:"}, {"fred"})
    assert cmd.options.release_control == release_control


def test_none_resets() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=:all:", "--all-releases=:none:"])
    release_control = ReleaseControl(set(), set())
    assert cmd.options.release_control == release_control


def test_none_preserves_other_side() -> None:
    cmd = SimpleCommand()
    cmd.main(
        ["fake", "--all-releases=:all:", "--only-final=fred", "--all-releases=:none:"]
    )
    release_control = ReleaseControl(set(), {"fred"})
    assert cmd.options.release_control == release_control


def test_comma_separated_values() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=pkg1,pkg2,pkg3"])
    release_control = ReleaseControl({"pkg1", "pkg2", "pkg3"}, set())
    assert cmd.options.release_control == release_control


@pytest.mark.parametrize(
    "all_releases,only_final,package,expected",
    [
        # Package specifically in all_releases
        ({"fred"}, set(), "fred", True),
        # Package specifically in all_releases, even with :all: in only_final
        ({"fred"}, {":all:"}, "fred", True),
        # Package specifically in only_final
        (set(), {"fred"}, "fred", False),
        # Package specifically in only_final, even with :all: in all_releases
        ({":all:"}, {"fred"}, "fred", False),
        # No specific setting, :all: in all_releases
        ({":all:"}, set(), "fred", True),
        # No specific setting, :all: in only_final
        (set(), {":all:"}, "fred", False),
        # No specific setting at all
        (set(), set(), "fred", None),
    ],
)
def test_allows_prereleases(
    all_releases: set[str], only_final: set[str], package: str, expected: bool | None
) -> None:
    rc = ReleaseControl(all_releases, only_final)
    assert rc.allows_prereleases(canonicalize_name(package)) == expected


def test_order_tracking_all_releases() -> None:
    """Test that order is tracked for --all-releases."""
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=pkg1", "--all-releases=pkg2"])

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("all_releases", "pkg1"),
        ("all_releases", "pkg2"),
    ]


def test_order_tracking_only_final() -> None:
    """Test that order is tracked for --only-final."""
    cmd = SimpleCommand()
    cmd.main(["fake", "--only-final=pkg1", "--only-final=pkg2"])

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("only_final", "pkg1"),
        ("only_final", "pkg2"),
    ]


def test_order_tracking_mixed() -> None:
    """Test that order is tracked when mixing --all-releases and --only-final."""
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--all-releases=pkg1",
            "--only-final=pkg2",
            "--all-releases=pkg3",
        ]
    )

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("all_releases", "pkg1"),
        ("only_final", "pkg2"),
        ("all_releases", "pkg3"),
    ]


def test_order_tracking_all_special() -> None:
    """Test that order is tracked for :all: special value."""
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=:all:", "--only-final=pkg1"])

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("all_releases", ":all:"),
        ("only_final", "pkg1"),
    ]


def test_order_tracking_critical_case() -> None:
    """Test the critical case: --only-final=:all: --all-releases=pkg."""
    cmd = SimpleCommand()
    cmd.main(["fake", "--only-final=:all:", "--all-releases=pkg1"])

    ordered_args = cmd.options.release_control.get_ordered_args()
    # The order should be preserved: only_final first, then all_releases
    assert ordered_args == [
        ("only_final", ":all:"),
        ("all_releases", "pkg1"),
    ]


def test_order_tracking_none_reset() -> None:
    """Test that :none: is tracked in order."""
    cmd = SimpleCommand()
    cmd.main(
        [
            "fake",
            "--all-releases=:all:",
            "--all-releases=:none:",
            "--all-releases=pkg1",
        ]
    )

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("all_releases", ":all:"),
        ("all_releases", ":none:"),
        ("all_releases", "pkg1"),
    ]


def test_order_tracking_comma_separated() -> None:
    """Test that comma-separated values are tracked individually."""
    cmd = SimpleCommand()
    cmd.main(["fake", "--all-releases=pkg1,pkg2,pkg3"])

    ordered_args = cmd.options.release_control.get_ordered_args()
    assert ordered_args == [
        ("all_releases", "pkg1"),
        ("all_releases", "pkg2"),
        ("all_releases", "pkg3"),
    ]
