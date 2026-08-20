"""Tests the presentation style of exceptions."""

from __future__ import annotations

import io
import locale
import logging
import pathlib
import platform
import sys
import sysconfig
import textwrap
from collections.abc import Callable
from typing import Any, Final
from unittest.mock import patch

import pytest

from pip._vendor import rich
from pip._vendor.packaging.tags import Tag

from pip._internal.exceptions import DiagnosticPipError, ExternallyManagedEnvironment
from pip._internal.exceptions.wheel import (
    AndroidTag,
    IncompatibleWheelError,
    LinuxTag,
    MacOSTag,
    WindowsTag,
    _parse_platform_tag,
    diagnose_incompatible_wheel,
    iOSTag,
)
from pip._internal.utils.compatibility_tags import get_supported

from tests.lib import cpython_only, linux_only, macos_only
from tests.lib.output import render_to_text as rendered


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

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """)

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

        assert rendered_in_ascii(err, color=True) == textwrap.dedent(f"""\
            {esc("1;31")}error{esc("0")}: {esc("1")}test-diagnostic{esc("0")}

            Oh no!
            It broke.

            Something went wrong
            very wrong.

            {esc("1;35")}note{esc("0")}: You did something wrong.
            {esc("1;36")}hint{esc("0")}: Do it better next time, by trying harder.
            """)

    def test_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """)

    def test_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            hint: Do it better next time, by trying harder.
            """)

    def test_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.

            note: You did something wrong, which is what caused this error.
            """)

    def test_no_context_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            note: You did something wrong, which is what caused this error.
            """)

    def test_no_context_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            hint: Do it better next time, by trying harder.
            """)

    def test_no_hint_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(

            Something went wrong
            very wrong.
            """)

    def test_no_hint_no_note_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            hint_stmt=None,
            note_stmt=None,
        )

        assert rendered_in_ascii(err) == textwrap.dedent("""\
            error: test-diagnostic

            Oh no!
            It broke. :(
            """)


def _current_version_tag(*, major_offset: int = 0, minor_offset: int = 0) -> str:
    major = sys.version_info.major + major_offset
    minor = sys.version_info.minor + minor_offset
    return f"{major}{minor}"


def _mock_get_config_var(**kwd: object) -> Callable[[str], Any]:
    """
    Patch sysconfig.get_config_var for arbitrary keys.
    """
    get_config_var = sysconfig.get_config_var

    def _mocked_get_config_var(var: str) -> Any:
        if var in kwd:
            return kwd[var]
        return get_config_var(var)

    return _mocked_get_config_var


class TestDiagnosticPipErrorPresentation_Unicode:
    def test_complete(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """)

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

        assert rendered(err, color=True) == textwrap.dedent(f"""\
            {esc("1;31")}error{esc("0")}: {esc("1")}test-diagnostic{esc("0")}

            {esc("31")}×{esc("0")} Oh no!
            {esc("31")}│{esc("0")} It broke.
            {esc("31")}╰─>{esc("0")} Something went wrong
            {esc("31")}   {esc("0")} very wrong.

            {esc("1;35")}note{esc("0")}: You did something wrong.
            {esc("1;36")}hint{esc("0")}: Do it better next time, by trying harder.
            """)

    def test_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            note: You did something wrong, which is what caused this error.
            hint: Do it better next time, by trying harder.
            """)

    def test_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            hint: Do it better next time, by trying harder.
            """)

    def test_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.

            note: You did something wrong, which is what caused this error.
            """)

    def test_no_context_no_hint(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt="You did something wrong, which is what caused this error.",
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            note: You did something wrong, which is what caused this error.
            """)

    def test_no_context_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            note_stmt=None,
            hint_stmt="Do it better next time, by trying harder.",
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
              It broke. :(

            hint: Do it better next time, by trying harder.
            """)

    def test_no_hint_no_note(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context="Something went wrong\nvery wrong.",
            note_stmt=None,
            hint_stmt=None,
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
            │ It broke. :(
            ╰─> Something went wrong
                very wrong.
            """)

    def test_no_hint_no_note_no_context(self) -> None:
        err = DiagnosticPipError(
            reference="test-diagnostic",
            message="Oh no!\nIt broke. :(",
            context=None,
            hint_stmt=None,
            note_stmt=None,
        )

        assert rendered(err) == textwrap.dedent("""\
            error: test-diagnostic

            × Oh no!
              It broke. :(
            """)


class TestIncompatibleWheelDiagnostic:
    supported_tags: Final[frozenset[Tag]] = frozenset(get_supported())
    supported_platforms: Final[frozenset[str]] = frozenset(
        t.platform for t in get_supported()
    )

    @pytest.mark.parametrize(
        "raw_tag, expected",
        [
            ("win_amd64", WindowsTag("amd64")),
            ("macosx_11_0_arm64", MacOSTag("arm64", (11, 0))),
            ("manylinux_2_28_x86_64", LinuxTag("glibc", (2, 28), "x86_64")),
            ("manylinux2014_x86_64", LinuxTag("glibc", (2, 17), "x86_64")),
            ("musllinux_1_2_x86_64", LinuxTag("musl", (1, 2), "x86_64")),
            ("android_27_arm64_v8a", AndroidTag()),
            ("ios_13_0_arm64_iphonesimulator", iOSTag()),
            ("freebsd_13_x86_64", None),
            ("windows_amd64", None),
            ("linux_x86_64", None),
            ("macosx_notreal", None),
        ],
    )
    def test_parse_platform_tag(self, raw_tag: str, expected: object) -> None:
        assert _parse_platform_tag(raw_tag) == expected

    def test_diagnose_python_major_version(self) -> None:
        current_major = sys.version_info.major
        filename = "sample-1.0-py9-none-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires Python 9+ (current: {current_major})"
        )

    @cpython_only
    def test_diagnose_cpython_minor_version(self) -> None:
        future = _current_version_tag(minor_offset=1)
        filename = f"sample-1.0-cp{future}-cp{future}-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires Python {sys.version_info.major}."
            f"{sys.version_info.minor + 1} "
            f"(current: {sys.version_info.major}.{sys.version_info.minor})"
        )

    @cpython_only
    @pytest.mark.skipif(
        sysconfig.get_config_var("Py_GIL_DISABLED") or False, reason="GIL-build only"
    )
    def test_diagnose_cpython_abi3_uses_minimum_version(self) -> None:
        """Test that abi3 wheels use Python version as a minimum."""
        current = _current_version_tag()
        future = _current_version_tag(minor_offset=1)
        filename = f"sample-1.0-cp{future}-abi3-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires Python {sys.version_info.major}."
            f"{sys.version_info.minor + 1}+ "
            f"(current: {sys.version_info.major}.{sys.version_info.minor})"
        )

        filename = f"sample-1.0-cp{current}-abi3-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) is None

    def test_diagnose_python_implementation(self) -> None:
        if sys.implementation.name.lower() == "pypy":
            other_implementation = "cp"
            expected = "cpython"
        else:
            other_implementation = "pp"
            expected = "pypy"
        filename = f"sample-1.0-{other_implementation}3-none-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires a different Python implementation: {expected}"
            f" (current: {sys.implementation.name})"
        )

    @pytest.mark.skipif(
        sys.version_info < (3, 13),
        reason="free-threaded Python was only introduced in 3.13",
    )
    @cpython_only
    def test_diagnose_abi_free_threaded_wheel(self) -> None:
        current = _current_version_tag()
        filename = f"sample-1.0-cp{current}-cp{current}t-any.whl"
        supported_tags = frozenset([Tag(f"cp{current}", f"cp{current}", "any")])

        with patch(
            "pip._internal.exceptions.wheel.sysconfig.get_config_var",
            _mock_get_config_var(Py_GIL_DISABLED=0),
        ):
            assert diagnose_incompatible_wheel(filename, supported_tags) == (
                "Wheel only supports free-threaded Python"
            )

    @pytest.mark.skipif(
        sys.version_info < (3, 13),
        reason="free-threaded Python was only introduced in 3.13",
    )
    @cpython_only
    def test_diagnose_abi_non_free_threaded_wheel(self) -> None:
        current = _current_version_tag()
        filename = f"sample-1.0-cp{current}-cp{current}-any.whl"
        supported_tags = frozenset([Tag(f"cp{current}", f"cp{current}t", "any")])

        with patch(
            "pip._internal.exceptions.wheel.sysconfig.get_config_var",
            _mock_get_config_var(Py_GIL_DISABLED=1),
        ):
            assert diagnose_incompatible_wheel(filename, supported_tags) == (
                "Wheel only supports non free-threaded Python"
            )

    def test_diagnose_abi_unknown(self) -> None:
        filename = "sample-1.0-py3-notanabi-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            "Wheel ABI is unsupported: notanabi"
        )

    def test_diagnose_prioritizes_platform_over_python_and_abi(self) -> None:
        future_major = sys.version_info.major + 1
        filename = f"sample-1.0-py{future_major}-notanabi-fakeplat.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            "Wheel requires a different platform: fakeplat"
        )

    def test_diagnose_prioritizes_python_over_abi(self) -> None:
        filename = "sample-1.0-py9-notanabi-any.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires Python 9 (current: {sys.version_info.major})"
        )

    def test_diagnose_platform_different_os(self) -> None:
        if platform.system() == "Windows":
            wheel_platform = "manylinux_2_17_x86_64"
            expected = "Linux"
        elif platform.system() == "Darwin":
            wheel_platform = "android_27_arm64_v8a"
            expected = "Android"
        else:
            wheel_platform = "win_amd64"
            expected = "Windows"

        filename = f"sample-1.0-py3-none-{wheel_platform}.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            f"Wheel requires {expected}"
        )

    @linux_only
    def test_diagnose_platform_linux_libc(self) -> None:
        libc, _ = platform.libc_ver()
        if libc == "glibc":
            wheel_platform = "musllinux_1_0_x86_64"
            expected = "Wheel requires musl (current: glibc)"
        elif libc == "musl":
            wheel_platform = "manylinux_1_0_x86_64"
            expected = "Wheel requires glibc (current: musl)"
        else:
            pytest.skip("unsupported Linux libc")

        filename = f"sample-1.0-py3-none-{wheel_platform}.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == expected

    @linux_only
    def test_diagnose_platform_linux_libc_version(self) -> None:
        libc, _ = platform.libc_ver()
        linux_tags = [
            tag
            for tag in map(_parse_platform_tag, self.supported_platforms)
            if isinstance(tag, LinuxTag) and tag.libc == libc
        ]
        if not linux_tags:
            pytest.skip(f"no supported {libc} platform tag")

        prefix = "manylinux" if libc == "glibc" else "musllinux"
        wheel_platform = f"{prefix}_99_99_{linux_tags[0].architecture}"
        filename = f"sample-1.0-py3-none-{wheel_platform}.whl"

        reason = diagnose_incompatible_wheel(filename, self.supported_tags)
        assert reason is not None
        assert reason.startswith(f"Wheel requires {libc} 99.99+")

    @macos_only
    def test_diagnose_platform_macos_version(self) -> None:
        macos_tags = [
            tag
            for tag in map(_parse_platform_tag, self.supported_platforms)
            if isinstance(tag, MacOSTag)
        ]
        if not macos_tags:
            pytest.skip("no supported macOS platform tag")

        wheel_platform = f"macosx_99_99_{macos_tags[0].architecture}"
        filename = f"sample-1.0-py3-none-{wheel_platform}.whl"

        reason = diagnose_incompatible_wheel(filename, self.supported_tags)
        assert reason is not None
        assert reason.startswith("Wheel requires macOS >= 99.99")

    def test_diagnose_platform_same_os_unsupported_architecture(self) -> None:
        current_system = platform.system()
        if current_system == "Windows":
            wheel_platform = "win_notrealarch"
        elif current_system == "Darwin":
            wheel_platform = "macosx_10_1_notrealarch"
        elif current_system == "Linux":
            libc, _ = platform.libc_ver()
            prefix = "manylinux" if libc == "glibc" else "musllinux"
            wheel_platform = f"{prefix}_1_0_notrealarch"
        else:
            pytest.skip("unsupported host platform")

        filename = f"sample-1.0-py3-none-{wheel_platform}.whl"
        reason = diagnose_incompatible_wheel(filename, self.supported_tags)
        assert reason is not None
        assert reason.startswith("Wheel architecture is unsupported: notrealarch")

    def test_diagnose_platform_unknown(self) -> None:
        filename = "sample-1.0-py3-none-fakeplat.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            "Wheel requires a different platform: fakeplat"
        )

    def test_diagnose_multi_tag_common_reason(self) -> None:
        """Test that a shared incompatibility reason is reported once."""
        filename = "sample-1.0-py2.py3-none-fakeplat.whl"
        assert diagnose_incompatible_wheel(filename, self.supported_tags) == (
            "Wheel requires a different platform: fakeplat"
        )

    def test_diagnose_multi_tag_mixed_reasons(self) -> None:
        """Test that mixed incompatibility reasons fall back to listing wheel tags."""
        filename = "sample-1.0-py3-none-mysupercomputer.fakeplat.whl"
        reason = diagnose_incompatible_wheel(filename, self.supported_tags)
        assert reason is not None
        assert reason.startswith("None of the wheel's tags match")
        assert "py3-none-mysupercomputer" in reason
        assert "py3-none-fakeplat" in reason

    def test_diagnostic_renders_reason_and_hint(self) -> None:
        current_major = sys.version_info.major
        future_major = current_major + 1
        filename = f"sample-1.0-py{future_major}-none-any.whl"
        reason = diagnose_incompatible_wheel(filename, self.supported_tags)
        err = IncompatibleWheelError(filename, reason)
        assert rendered(err) == textwrap.dedent(f"""\
            error: incompatible-wheel

            × {filename} is incompatible
            ╰─> Wheel requires Python {future_major}+ (current: {current_major})

            hint: Run 'pip debug -v' for a list of compatible tags for your system.
            """)


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

        def fake_getlocale(category: int) -> tuple[str | None, str | None]:
            """Fake getlocale() that always reports zh_Hant for LC_MESSAGES."""
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
