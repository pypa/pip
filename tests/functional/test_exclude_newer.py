"""Tests for pip install --exclude-newer-than."""

from __future__ import annotations

import pytest

from tests.lib import PipTestEnvironment, TestData


class TestExcludeNewer:
    """Test --exclude-newer-than functionality."""

    def test_exclude_newer_than_invalid_date(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that --exclude-newer-than fails with invalid date format."""
        result = script.pip_install_local(
            "--exclude-newer-than=invalid-date", "simple", expect_error=True
        )

        # Should fail with date parsing error
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_exclude_newer_than_help_text(self, script: PipTestEnvironment) -> None:
        """Test that --exclude-newer-than appears in help text."""
        result = script.pip("install", "--help")
        assert "--exclude-newer-than" in result.stdout
        assert "datetime" in result.stdout

    @pytest.mark.parametrize("command", ["install", "download", "wheel"])
    def test_exclude_newer_than_available_in_commands(
        self, script: PipTestEnvironment, command: str
    ) -> None:
        """Test that --exclude-newer-than is available in relevant commands."""
        result = script.pip(command, "--help")
        assert "--exclude-newer-than" in result.stdout

    @pytest.mark.network
    def test_exclude_newer_than_with_real_pypi(
        self, script: PipTestEnvironment
    ) -> None:
        """Test exclude-newer functionality against real PyPI with upload times."""
        # Use a small package with known old versions for testing
        # requests 2.0.0 was released in 2013

        # Test 1: With an old cutoff date, should find no matching versions
        result = script.pip(
            "install",
            "--dry-run",
            "--no-deps",
            "--exclude-newer-than=2010-01-01T00:00:00",
            "requests==2.0.0",
            expect_error=True,
        )
        # Should fail because requests 2.0.0 was uploaded after 2010
        assert "No matching distribution found" in result.stderr

        # Test 2: With a date that should find the package
        result = script.pip(
            "install",
            "--dry-run",
            "--no-deps",
            "--exclude-newer-than=2030-01-01T00:00:00",
            "requests==2.0.0",
            expect_error=False,
        )
        assert "Would install requests-2.0.0" in result.stdout

    @pytest.mark.network
    def test_exclude_newer_than_date_formats(self, script: PipTestEnvironment) -> None:
        """Test different date formats work with real PyPI."""
        # Test various date formats with a well known small package
        formats = [
            "2030-01-01",
            "2030-01-01T00:00:00",
            "2030-01-01T00:00:00+00:00",
            "2030-01-01T00:00:00-05:00",
        ]

        for date_format in formats:
            result = script.pip(
                "install",
                "--dry-run",
                "--no-deps",
                f"--exclude-newer-than={date_format}",
                "requests==2.0.0",
                expect_error=False,
            )
            # All dates should allow the package
            assert "Would install requests-2.0.0" in result.stdout
