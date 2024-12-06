"""Tests the presentation style of exceptions."""

import io
import locale
import logging
import pathlib
import sys
import textwrap
from typing import Optional, Tuple

import pytest

from pip._vendor import rich

from pip._internal.exceptions import DiagnosticPipError, ExternallyManagedEnvironment


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


class TestExternallyManagedEnvironment:
    default_text = (
        f"The Python environment under {sys.prefix} is managed externally, "
        f"and may not be\nmanipulated by the user. Please use specific "
        f"tooling from the distributor of\nthe Python installation to "
        f"interact with this environment instead.\n"
    )

    @pytest.fixture(autouse=True)
    def patch_locale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        orig_getlocal = locale.getlocale

        def fake_getlocale(category: int) -> Tuple[Optional[str], Optional[str]]:
            """Fake getlocale() that always reports zh_Hant for LC_MESSASGES."""
            result = orig_getlocal(category)
            if category == getattr(locale, "LC_MESSAGES", None):
                return "zh_Hant", result[1]
            return result

        monkeypatch.setattr(locale, "getlocale", fake_getlocale)

    @pytest.fixture
    def marker(self, tmp_path: pathlib.Path) -> pathlib.Path:
        marker = tmp_path.joinpath("EXTERNALLY-MANAGED")
        marker.touch()
        return marker

    def test_invalid_config_format(
        self,
        caplog: pytest.LogCaptureFixture,
        marker: pathlib.Path,
    ) -> None:
        marker.write_text("invalid", encoding="utf8")

        with caplog.at_level(logging.WARNING, "pip._internal.exceptions"):
            exc = ExternallyManagedEnvironment.from_config(marker)
        assert len(caplog.records) == 1
        assert caplog.records[-1].getMessage() == f"Failed to read {marker}"

        assert str(exc.context) == self.default_text

    @pytest.mark.parametrize(
        "config",
        [
            pytest.param("", id="empty"),
            pytest.param("[foo]\nblah = blah", id="no-section"),
            pytest.param("[externally-managed]\nblah = blah", id="no-key"),
        ],
    )
    def test_config_without_key(
        self,
        caplog: pytest.LogCaptureFixture,
        marker: pathlib.Path,
        config: str,
    ) -> None:
        marker.write_text(config, encoding="utf8")

        with caplog.at_level(logging.WARNING, "pip._internal.exceptions"):
            exc = ExternallyManagedEnvironment.from_config(marker)
        assert not caplog.records
        assert str(exc.context) == self.default_text

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Localization disabled on Windows",
    )
    @pytest.mark.parametrize(
        "config, expected",
        [
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                Error-zh = 中文
                Error-zh_Hant = 繁體
                Error-zh_Hans = 简体
                """,
                "繁體",
                id="full",
            ),
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                Error-zh = 中文
                Error-zh_Hans = 简体
                """,
                "中文",
                id="no-variant",
            ),
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                """,
                "最後",
                id="fallback",
            ),
        ],
    )
    def test_config_canonical(
        self,
        caplog: pytest.LogCaptureFixture,
        marker: pathlib.Path,
        config: str,
        expected: str,
    ) -> None:
        marker.write_text(
            textwrap.dedent(config),
            encoding="utf8",
        )

        with caplog.at_level(logging.WARNING, "pip._internal.exceptions"):
            exc = ExternallyManagedEnvironment.from_config(marker)
        assert not caplog.records
        assert str(exc.context) == expected

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Non-Windows should implement localization",
    )
    @pytest.mark.parametrize(
        "config",
        [
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                Error-zh = 中文
                Error-zh_Hant = 繁體
                Error-zh_Hans = 简体
                """,
                id="full",
            ),
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                Error-zh = 中文
                Error-zh_Hans = 简体
                """,
                id="no-variant",
            ),
            pytest.param(
                """\
                [externally-managed]
                Error = 最後
                Error-en = English
                """,
                id="fallback",
            ),
        ],
    )
    def test_config_canonical_no_localization(
        self,
        caplog: pytest.LogCaptureFixture,
        marker: pathlib.Path,
        config: str,
    ) -> None:
        marker.write_text(
            textwrap.dedent(config),
            encoding="utf8",
        )

        with caplog.at_level(logging.WARNING, "pip._internal.exceptions"):
            exc = ExternallyManagedEnvironment.from_config(marker)
        assert not caplog.records
        assert str(exc.context) == "最後"
