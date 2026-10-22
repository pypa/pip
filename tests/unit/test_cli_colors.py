import optparse

import pytest

import pip._internal.cli.parser


def test_option_error_usage_is_rendered(capsys: pytest.CaptureFixture[str]) -> None:
    formatter = pip._internal.cli.parser.PrettyHelpFormatter()
    parser = pip._internal.cli.parser.ConfigOptionParser(
        usage="\n%prog [options]",
        name="test",
        formatter=formatter,
    )

    with pytest.raises(SystemExit):
        parser.error("no such option: --updgrade")

    stderr = capsys.readouterr().err
    assert "no such option: --updgrade" in stderr
    assert "Usage:" in stderr
    assert "[optparse." not in stderr
    assert "\\[options]" not in stderr


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
