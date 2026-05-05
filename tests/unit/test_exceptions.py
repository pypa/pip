"""Tests the presentation style of exceptions."""

from __future__ import annotations

import io
import locale
import logging
import pathlib
import sys
import textwrap
from typing import cast
from unittest import mock

import pytest

from pip._vendor import rich
from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.version import InvalidVersion

from pip._internal.exceptions import (
    BuildDependencyInstallError,
    DiagnosticPipError,
    ExternallyManagedEnvironment,
    IncompleteDownloadError,
    InstallWheelBuildError,
    InvalidInstalledPackage,
    LegacyDistutilsInstall,
    MetadataGenerationFailed,
    MissingPyProjectBuildRequires,
    ResolutionTooDeepError,
    UninstallMissingRecord,
)
from pip._internal.req.req_install import InstallRequirement


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


# ---------------------------------------------------------------------------
# Helpers shared by the concrete-exception tests below
# ---------------------------------------------------------------------------

def _make_fake_dist(
    raw_name: str = "my-package",
    version: str = "1.0",
    installer: str = "pip",
    installed_location: str | None = "/fake/location",
) -> mock.MagicMock:
    """Return a minimal mock that satisfies BaseDistribution's interface."""
    dist = mock.MagicMock()
    dist.raw_name = raw_name
    dist.version = version
    dist.installer = installer
    dist.installed_location = installed_location
    dist.configure_mock(**{"__str__.return_value": f"{raw_name} {version}"})
    return dist


def _make_fake_ireq(name: str = "mypackage") -> mock.MagicMock:
    """Return a minimal mock that satisfies InstallRequirement's interface."""
    ireq = mock.MagicMock()
    ireq.configure_mock(**{"__str__.return_value": name})
    ireq.name = name
    return ireq


def _make_fake_link(url: str = "https://example.com/pkg.tar.gz") -> mock.MagicMock:
    link = mock.MagicMock()
    link.redacted_url = url
    return link


# ---------------------------------------------------------------------------
# Tests for concrete DiagnosticPipError subclasses
# ---------------------------------------------------------------------------


class TestMissingPyProjectBuildRequires:
    def test_message_contains_package_name(self) -> None:
        err = MissingPyProjectBuildRequires(package="mypackage")
        assert "mypackage" in rendered(err)

    def test_reference(self) -> None:
        err = MissingPyProjectBuildRequires(package="mypackage")
        assert err.reference == "missing-pyproject-build-system-requires"

    def test_note_blames_package_not_pip(self) -> None:
        err = MissingPyProjectBuildRequires(package="mypackage")
        output = rendered(err)
        assert "not pip" in output

    def test_hint_references_pep518(self) -> None:
        err = MissingPyProjectBuildRequires(package="mypackage")
        assert "PEP 518" in rendered(err)


class TestResolutionTooDeepError:
    def test_reference(self) -> None:
        err = ResolutionTooDeepError()
        assert err.reference == "resolution-too-deep"

    def test_message_mentions_depth(self) -> None:
        err = ResolutionTooDeepError()
        output = rendered(err)
        assert "depth" in output.lower()

    def test_includes_docs_link(self) -> None:
        err = ResolutionTooDeepError()
        assert err.link is not None
        assert "pip.pypa.io" in err.link

    def test_hint_suggests_lower_bounds(self) -> None:
        err = ResolutionTooDeepError()
        output = rendered(err)
        assert "lower bounds" in output


class TestUninstallMissingRecord:
    def test_reference(self) -> None:
        dist = _make_fake_dist()
        err = UninstallMissingRecord(distribution=dist)
        assert err.reference == "uninstall-no-record-file"

    def test_message_contains_distribution(self) -> None:
        dist = _make_fake_dist(raw_name="badpkg", version="2.0")
        err = UninstallMissingRecord(distribution=dist)
        output = rendered(err)
        assert "badpkg" in output

    def test_hint_for_pip_installer_suggests_reinstall(self) -> None:
        dist = _make_fake_dist(installer="pip")
        err = UninstallMissingRecord(distribution=dist)
        output = rendered(err)
        assert "pip install" in output

    def test_hint_for_other_installer_names_installer(self) -> None:
        dist = _make_fake_dist(installer="conda")
        err = UninstallMissingRecord(distribution=dist)
        output = rendered(err)
        assert "conda" in output

    def test_hint_for_empty_installer_suggests_reinstall(self) -> None:
        # An empty installer string should be treated the same as "pip".
        dist = _make_fake_dist(installer="")
        err = UninstallMissingRecord(distribution=dist)
        output = rendered(err)
        assert "pip install" in output


class TestLegacyDistutilsInstall:
    def test_reference(self) -> None:
        dist = _make_fake_dist()
        err = LegacyDistutilsInstall(distribution=dist)
        assert err.reference == "uninstall-distutils-installed-package"

    def test_message_contains_distribution(self) -> None:
        dist = _make_fake_dist(raw_name="legacypkg", version="0.1")
        err = LegacyDistutilsInstall(distribution=dist)
        output = rendered(err)
        assert "legacypkg" in output

    def test_context_mentions_distutils(self) -> None:
        dist = _make_fake_dist()
        err = LegacyDistutilsInstall(distribution=dist)
        assert err.context is not None
        assert "distutils" in str(err.context)


class TestInvalidInstalledPackage:
    def test_reference(self) -> None:
        dist = _make_fake_dist()
        exc = InvalidRequirement("bad requirement")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        assert err.reference == "invalid-installed-package"

    def test_message_with_invalid_requirement(self) -> None:
        dist = _make_fake_dist(raw_name="badpkg", version="1.0")
        exc = InvalidRequirement("bad requirement")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        output = rendered(err)
        assert "badpkg" in output
        assert "requirement" in output

    def test_message_with_invalid_version(self) -> None:
        dist = _make_fake_dist(raw_name="badpkg", version="1.0")
        exc = InvalidVersion("not-a-version")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        output = rendered(err)
        assert "badpkg" in output
        assert "version" in output

    def test_hint_suggests_uninstall(self) -> None:
        dist = _make_fake_dist()
        exc = InvalidRequirement("bad")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        output = rendered(err)
        assert "uninstall" in output.lower()

    def test_installed_location_included_when_present(self) -> None:
        dist = _make_fake_dist(installed_location="/some/path")
        exc = InvalidRequirement("bad")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        output = rendered(err)
        assert "/some/path" in output

    def test_no_location_when_absent(self) -> None:
        dist = _make_fake_dist(installed_location=None)
        exc = InvalidRequirement("bad")
        err = InvalidInstalledPackage(dist=dist, invalid_exc=exc)
        # Should not crash, location line should simply be absent
        output = rendered(err)
        assert "None" not in output


class TestMetadataGenerationFailed:
    def test_reference(self) -> None:
        err = MetadataGenerationFailed(package_details="mypackage 1.0")
        assert err.reference == "metadata-generation-failed"

    def test_message_is_generic(self) -> None:
        err = MetadataGenerationFailed(package_details="mypackage 1.0")
        output = rendered(err)
        assert "metadata" in output.lower()

    def test_package_details_in_context(self) -> None:
        err = MetadataGenerationFailed(package_details="mypackage 1.0")
        assert "mypackage" in str(err.context)

    def test_str_representation(self) -> None:
        err = MetadataGenerationFailed(package_details="mypackage 1.0")
        assert "metadata generation failed" in str(err)


class TestInstallWheelBuildError:
    def _make_ireq(self, name: str) -> InstallRequirement:
        ireq = mock.MagicMock(spec=InstallRequirement)
        ireq.name = name
        return cast(InstallRequirement, ireq)

    def test_reference(self) -> None:
        err = InstallWheelBuildError(failed=[self._make_ireq("pkgA")])
        assert err.reference == "failed-wheel-build-for-install"

    def test_context_lists_failed_packages(self) -> None:
        ireqs = [self._make_ireq("pkgA"), self._make_ireq("pkgB")]
        err = InstallWheelBuildError(failed=ireqs)
        output = rendered(err)
        assert "pkgA" in output
        assert "pkgB" in output

    def test_message_mentions_pyproject(self) -> None:
        err = InstallWheelBuildError(failed=[self._make_ireq("pkgA")])
        output = rendered(err)
        assert "pyproject.toml" in output


class TestIncompleteDownloadError:
    def _make_download(
        self,
        *,
        bytes_received: int = 500,
        size: int = 1000,
        reattempts: int = 0,
        url: str = "https://example.com/pkg.tar.gz",
    ) -> mock.MagicMock:
        download = mock.MagicMock()
        download.bytes_received = bytes_received
        download.size = size
        download.reattempts = reattempts
        download.link.redacted_url = url
        return download

    def test_reference(self) -> None:
        err = IncompleteDownloadError(self._make_download())
        assert err.reference == "incomplete-download"

    def test_url_in_context(self) -> None:
        err = IncompleteDownloadError(
            self._make_download(url="https://example.com/foo.whl")
        )
        assert "https://example.com/foo.whl" in str(err.context)

    def test_hint_without_retries_suggests_enabling_resume(self) -> None:
        err = IncompleteDownloadError(self._make_download(reattempts=0))
        assert err.hint_stmt is not None
        assert "resume" in str(err.hint_stmt).lower()

    def test_hint_with_retries_suggests_configuring_limit(self) -> None:
        err = IncompleteDownloadError(self._make_download(reattempts=3))
        assert err.hint_stmt is not None
        assert "resume-retries" in str(err.hint_stmt)

    def test_note_blames_network(self) -> None:
        err = IncompleteDownloadError(self._make_download())
        assert err.note_stmt is not None
        assert "network" in str(err.note_stmt).lower()


class TestBuildDependencyInstallError:
    def test_reference(self) -> None:
        cause = Exception("something went wrong")
        err = BuildDependencyInstallError(
            req=None,
            build_reqs=["setuptools>=40"],
            cause=cause,
            log_lines=None,
        )
        assert err.reference == "failed-build-dependency-install"

    def test_message_when_no_req(self) -> None:
        cause = Exception("oops")
        err = BuildDependencyInstallError(
            req=None,
            build_reqs=["wheel"],
            cause=cause,
            log_lines=None,
        )
        output = rendered(err)
        assert "build dependencies" in output.lower()

    def test_message_includes_req_when_present(self) -> None:
        ireq = _make_fake_ireq("mypkg")
        cause = Exception("oops")
        err = BuildDependencyInstallError(
            req=ireq,
            build_reqs=["wheel"],
            cause=cause,
            log_lines=None,
        )
        output = rendered(err)
        assert "mypkg" in output

    def test_note_for_unexpected_exception_asks_to_file_issue(self) -> None:
        cause = RuntimeError("unexpected")
        err = BuildDependencyInstallError(
            req=None,
            build_reqs=["wheel"],
            cause=cause,
            log_lines=None,
        )
        assert err.note_stmt is not None
        assert "issue" in str(err.note_stmt).lower()

    def test_note_for_pip_error_says_not_pip_problem(self) -> None:
        from pip._internal.exceptions import PipError

        cause = PipError("a pip error")
        err = BuildDependencyInstallError(
            req=None,
            build_reqs=["wheel"],
            cause=cause,
            log_lines=None,
        )
        assert err.note_stmt is not None
        assert "not a problem with pip" in str(err.note_stmt).lower()

    def test_log_lines_appear_in_context(self) -> None:
        from pip._internal.exceptions import PipError

        cause = PipError("detail error")
        err = BuildDependencyInstallError(
            req=None,
            build_reqs=["wheel"],
            cause=cause,
            log_lines=["step 1 output", "step 2 output"],
        )
        context_str = str(err.context)
        assert "step 1 output" in context_str
        assert "step 2 output" in context_str