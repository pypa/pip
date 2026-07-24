"""Tests for pip --uploaded-prior-to."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.lib import PipTestEnvironment, TestData
from tests.lib.server import (
    file_response,
    json_index_page,
    make_mock_server,
    package_page,
    server_running,
)

if TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment


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
            "--no-build-isolation",
            "--index-url",
            data.index_url("simple"),
            "--uploaded-prior-to=2100-01-01T00:00:00",
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
                "--uploaded-prior-to=2100-01-01T00:00:00",
                "simple",
                expect_error=True,
            )

        assert "does not provide upload-time metadata" in result.stderr

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
        result = script.pip_install_local(
            "--uploaded-prior-to=2000-01-01T00:00:00", "simple==1.0"
        )
        assert "Successfully installed simple-1.0" in result.stdout

    def test_uploaded_prior_to_list_outdated(self, script: PipTestEnvironment) -> None:
        """Test that list --outdated applies upload-time filtering to Latest."""
        script.pip_install_local("simple==1.0")

        files = [
            {
                "url": "simple-1.0.tar.gz",
                "hashes": {},
                "upload-time": "2020-01-01T00:00:00Z",
            },
            {
                "url": "simple-2.0.tar.gz",
                "hashes": {},
                "upload-time": "2020-06-01T00:00:00Z",
            },
            {
                "url": "simple-3.0.tar.gz",
                "hashes": {},
                "upload-time": "2021-01-01T00:00:00Z",
            },
        ]

        def index_router(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> WSGIApplication:
            name = environ["PATH_INFO"].strip("/")
            return json_index_page(name, files if name == "simple" else [])

        server = make_mock_server()
        server.mock.side_effect = index_router

        with server_running(server):
            args = [
                "list",
                "--index-url",
                f"http://{server.host}:{server.port}",
                "--format=json",
            ]

            result = script.pip(*args, "--outdated")
            assert {
                "name": "simple",
                "version": "1.0",
                "latest_version": "3.0",
                "latest_filetype": "sdist",
            } in json.loads(result.stdout)

            result = script.pip(
                *args, "--outdated", "--uploaded-prior-to=2020-12-31T00:00:00Z"
            )
            assert {
                "name": "simple",
                "version": "1.0",
                "latest_version": "2.0",
                "latest_filetype": "sdist",
            } in json.loads(result.stdout)

            result = script.pip(
                *args, "--outdated", "--uploaded-prior-to=2020-03-01T00:00:00Z"
            )
            assert "simple" not in {p["name"] for p in json.loads(result.stdout)}

            # The same cutoff must leave 1.0 as the best candidate, making the
            # package up-to-date rather than filtered out entirely.
            result = script.pip(
                *args, "--uptodate", "--uploaded-prior-to=2020-03-01T00:00:00Z"
            )
            assert {"name": "simple", "version": "1.0"} in json.loads(result.stdout)

    def test_uploaded_prior_to_list_outdated_no_upload_time(
        self, script: PipTestEnvironment
    ) -> None:
        """Test that list --outdated errors if the index lacks upload-time."""
        script.pip_install_local("simple==1.0")

        def index_router(
            environ: WSGIEnvironment, start_response: StartResponse
        ) -> WSGIApplication:
            if environ["PATH_INFO"] == "/simple/":
                return package_page({"simple-2.0.tar.gz": "/files/simple-2.0.tar.gz"})
            return package_page({})

        server = make_mock_server()
        server.mock.side_effect = index_router

        with server_running(server):
            result = script.pip(
                "list",
                "--index-url",
                f"http://{server.host}:{server.port}",
                "--outdated",
                "--uploaded-prior-to=2100-01-01T00:00:00",
                expect_error=True,
            )

        assert "does not provide upload-time metadata" in result.stderr
