"""Tests the presentation style of exceptions."""

import textwrap

import pytest

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


class TestDiagnosticPipErrorPresentation_ASCII:
    def test_complete(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            attention_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            Note: You did something wrong, which is what caused this error.
            Hint: Do it better next time, by trying harder.
            """
        )

    def test_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            attention_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Note: You did something wrong, which is what caused this error.
            Hint: Do it better next time, by trying harder.
            """
        )

    def test_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            attention_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            Hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            attention_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            Note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            attention_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Note: You did something wrong, which is what caused this error.
            """
        )

    def test_no_context_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            attention_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(

            Hint: Do it better next time, by trying harder.
            """
        )

    def test_no_hint_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            attention_stmt=None,
            hint_stmt=None,
        )

        assert str(err) == textwrap.dedent(
            """\
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
            attention_stmt=None,
        )

        assert str(err) == textwrap.dedent(
            """\
            Oh no!
            It broke. :(
            """
        )
