"""Tests the presentation style of exceptions."""

import io
import textwrap

import pytest
from pip._vendor import rich

from pip._internal.exceptions import DiagnosticPipError


class TestDiagnosticPipErrorCreation:
    def test_fails_without_reference(self) -> None:
        class DerivedError(DiagnosticPipError):
            pass

        with pytest.raises(AssertionError) as exc_info:
            DerivedError(message="", context=None, hint_stmt=None)

        assert str(exc_info.value) == "error reference not provided!"

    def test_can_fetch_reference_from_subclass(self) -> None:
        class DerivedError(DiagnosticPipError):
            reference = "subclass-reference"

        obj = DerivedError(message="", context=None, hint_stmt=None)
        assert obj.reference == "subclass-reference"

    def test_can_fetch_reference_from_arguments(self) -> None:
        class DerivedError(DiagnosticPipError):
            pass

        obj = DerivedError(
            message="", context=None, hint_stmt=None, reference="subclass-reference"
        )
        assert obj.reference == "subclass-reference"

    @pytest.mark.parametrize(
        "name",
        [
            "BADNAME",
            "BadName",
            "bad_name",
            "BAD_NAME",
            "_bad",
            "bad-name-",
            "bad--name",
            "-bad-name",
            "bad-name-due-to-1-number",
        ],
    )
    def test_rejects_non_kebab_case_names(self, name: str) -> None:
        class DerivedError(DiagnosticPipError):
            reference = name

        with pytest.raises(AssertionError) as exc_info:
            DerivedError(message="", context=None, hint_stmt=None)

        assert str(exc_info.value) == "error reference must be kebab-case!"


def rendered_in_ascii(error: DiagnosticPipError, *, color: bool = False) -> str:
    with io.BytesIO() as stream:
        console = rich.console.Console(
            force_terminal=False,
            file=io.TextIOWrapper(stream, encoding="ascii", newline=""),
            color_system="truecolor" if color else None,
        )
        console.print(error)
        return stream.getvalue().decode("ascii")


class TestDiagnosticPipErrorPresentation_ASCII:
    def test_complete(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """
        )

    def test_complete_color(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke.",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        def esc(code: str = "0") -> str:
            return f"\x1b[{code}m"

        assert rendered_in_ascii(err, color=True) == textwrap.dedent(
            f"""\
            {esc("1;31")}error{esc("0")}: {esc("1")}test-diagnostic{esc("0")}

            Oh no!
            It broke.

            Something went wrong
            very wrong.

            {esc("1;35")}note{esc("0")}: You did something wrong.
            {esc("1;36")}hint{esc("0")}: Do it better next time, by trying harder.
            """
        )

    def test_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.
            """
        )

    def test_no_hint_no_note_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            hint_stmt=None,
            note_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            Oh no!
            It broke. :(
            """
        )


def rendered(error: DiagnosticPipError, *, color: bool = False) -> str:
    with io.StringIO() as stream:
        console = rich.console.Console(
            force_terminal=False,
            file=stream,
            color_system="truecolor" if color else None,
        )
        console.print(error)
        return stream.getvalue()


class TestDiagnosticPipErrorPresentation_Unicode:
    def test_complete(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """
        )

    def test_complete_color(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke.",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        def esc(code: str = "0") -> str:
            return f"\x1b[{code}m"

        assert rendered(err, color=True) == textwrap.dedent(
            f"""\
            {esc("1;31")}error{esc("0")}: {esc("1")}test-diagnostic{esc("0")}

            {esc("31")}×{esc("0")} Oh no!
            {esc("31")}│{esc("0")} It broke.
            {esc("31")}╰─>{esc("0")} Something went wrong
            {esc("31")}   {esc("0")} very wrong.

            {esc("1;35")}note{esc("0")}: You did something wrong.
            {esc("1;36")}hint{esc("0")}: Do it better next time, by trying harder.
            """
        )

    def test_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.
            """
        )

    def test_no_hint_no_note_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            hint_stmt=None,
            note_stmt=None,
        )

        assert rendered(err) == textwrap.dedent(
            """\
            error: test-diagnostic

            × Oh no!
              It broke. :(
            """
        )
