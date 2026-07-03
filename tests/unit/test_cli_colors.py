import io
import optparse

import pip._internal.cli.parser
from pip._internal.cli.parser import ConfigOptionParser, PrettyHelpFormatter


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


def test_print_usage_renders_rich_markup() -> None:
    """print_usage() must not emit raw Rich markup tags to the output stream.

    Regression test for https://github.com/pypa/pip/issues/14136:
    ConfigOptionParser.error() calls print_usage(sys.stderr), which previously
    fell through to the base optparse implementation and wrote raw markup such
    as ``[optparse.groups]Usage:[/]`` literally instead of rendering it.
    """
    parser = ConfigOptionParser(
        name="install",
        usage="%prog install [options] <requirement specifier>",
        formatter=PrettyHelpFormatter(),
    )
    buf = io.StringIO()
    parser.print_usage(file=buf)
    output = buf.getvalue()

    assert "[optparse.groups]" not in output, (
        f"Raw Rich markup found in print_usage() output: {output!r}"
    )
    assert "Usage:" in output, (
        f"Expected 'Usage:' in rendered output but got: {output!r}"
    )
