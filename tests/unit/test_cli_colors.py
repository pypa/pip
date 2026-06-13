import optparse

import pip._internal.cli.parser


def test_color_formatter_option_strings() -> None:
    formatter = pip._internal.cli.parser.PrettyHelpFormatter()
    strs = formatter.format_option_strings(
        optparse.Option(
            "--test-option",
            "-t",
            help="A test option for colors",
        )
    )

    assert (
        "[optparse.shortargs]-t[/], [optparse.longargs]--test-option[/]"
        " [optparse.metavar]<test_option>[/]" == strs
    )
