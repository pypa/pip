"""Tests for pip install --uploaded-prior-to."""

from __future__ import annotations

import pytest

from tests.lib import PipTestEnvironment, TestData
from tests.lib.server import (
    file_response,
    make_mock_server,
    package_page,
    server_running,
)


class TestUploadedPriorTo:
    """Test --uploaded-prior-to functionality."""

    def test_uploaded_prior_to_invalid_date(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that invalid date format is rejected."""
        result = script.pip_install_local(
            "--uploaded-prior-to=invalid-date", "simple", expect_error=True
        )
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_uploaded_prior_to_file_index_no_upload_time(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that file:// indexes are exempt from upload-time filtering."""
        result = script.pip(
            "install",
            "--index-url",
            data.index_url("simple"),
            "--uploaded-prior-to=3030-01-01T00:00:00",
            "simple",
            expect_error=False,
        )
        assert "Successfully installed simple" in result.stdout

    def test_uploaded_prior_to_http_index_no_upload_time(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that HTTP index without upload-time causes immediate error."""
        server = make_mock_server()
        simple_package = data.packages / "simple-1.0.tar.gz"
        server.mock.side_effect = [
            package_page({"simple-1.0.tar.gz": "/files/simple-1.0.tar.gz"}),
            file_response(simple_package),
        ]

        with server_running(server):
            result = script.pip(
                "install",
                "--index-url",
                f"http://{server.host}:{server.port}",
                "--uploaded-prior-to=3030-01-01T00:00:00",
                "simple",
                expect_error=True,
            )

        assert "does not provide upload-time metadata" in result.stderr
        assert "--uploaded-prior-to" in result.stderr or "Cannot use" in result.stderr

    @pytest.mark.network
    def test_uploaded_prior_to_with_real_pypi(self, script: PipTestEnvironment) -> None:
        """Test filtering against real PyPI with upload-time metadata."""
        # Test with old cutoff date - should find no matching versions
        result = script.pip(
            "install",
            "--dry-run",
            "--no-deps",
            "--uploaded-prior-to=2010-01-01T00:00:00",
            "requests==2.0.0",
            expect_error=True,
        )
        assert "Could not find a version that satisfies" in result.stderr

        # Test with future cutoff date - should find the package
        result = script.pip(
            "install",
            "--dry-run",
            "--no-deps",
            "--uploaded-prior-to=2030-01-01T00:00:00",
            "requests==2.0.0",
            expect_error=False,
        )
        assert "Would install requests-2.0.0" in result.stdout

    @pytest.mark.network
    def test_uploaded_prior_to_date_formats(self, script: PipTestEnvironment) -> None:
        """Test various date format strings are accepted."""
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
                f"--uploaded-prior-to={date_format}",
                "requests==2.0.0",
                expect_error=False,
            )
            assert "Would install requests-2.0.0" in result.stdout

    def test_uploaded_prior_to_allows_local_files(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that local file installs bypass upload-time filtering."""
        simple_wheel = data.packages / "simplewheel-1.0-py2.py3-none-any.whl"

        result = script.pip(
            "install",
            "--no-index",
            "--uploaded-prior-to=2000-01-01T00:00:00",
            str(simple_wheel),
            expect_error=False,
        )
        assert "Successfully installed simplewheel-1.0" in result.stdout

    def test_uploaded_prior_to_allows_find_links(
        self, script: PipTestEnvironment, data: TestData
    ) -> None:
        """Test that --find-links bypasses upload-time filtering."""
        result = script.pip(
            "install",
            "--no-index",
            "--find-links",
            data.find_links,
            "--uploaded-prior-to=2000-01-01T00:00:00",
            "simple==1.0",
            expect_error=False,
        )
        assert "Successfully installed simple-1.0" in result.stdout
