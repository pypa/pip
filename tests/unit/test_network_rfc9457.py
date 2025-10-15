"""Tests for RFC 9457 (Problem Details for HTTP APIs) support."""

import json

import pytest

from pip._internal.exceptions import HTTPProblemDetailsError, NetworkConnectionError
from pip._internal.network.rfc9457 import (
    ProblemDetails,
    is_problem_details_response,
    parse_problem_details,
)
from pip._internal.network.utils import raise_for_status
from tests.lib.requests_mocks import MockResponse


class TestProblemDetails:
    def test_from_dict(self) -> None:
        data = {
            "status": 404,
            "title": "Not Found",
            "detail": "Resource not found",
        }

        problem = ProblemDetails.from_dict(data)
        assert problem.status == 404
        assert problem.title == "Not Found"
        assert problem.detail == "Resource not found"

    def test_from_json(self) -> None:
        json_str = json.dumps({
            "status": 404,
            "title": "Not Found",
            "detail": "Resource not found",
        })

        problem = ProblemDetails.from_json(json_str)
        assert problem.status == 404
        assert problem.title == "Not Found"

    def test_string_representation(self) -> None:
        """Test string representation of ProblemDetails."""
        problem = ProblemDetails(
            status=403,
            title="Access Denied",
            detail="Your API token does not have permission",
        )

        str_repr = str(problem)
        assert "Access Denied" in str_repr
        assert "403" in str_repr
        assert "API token" in str_repr

class TestIsProblemDetailsResponse:
    def test_detects_problem_json_content_type(self) -> None:
        resp = MockResponse(b"")
        resp.headers = {"Content-Type": "application/problem+json"}

        assert is_problem_details_response(resp) is True

    def test_detects_problem_json_with_charset(self) -> None:
        resp = MockResponse(b"")
        resp.headers = {"Content-Type": "application/problem+json; charset=utf-8"}

        assert is_problem_details_response(resp) is True

    def test_does_not_detect_regular_json(self) -> None:
        resp = MockResponse(b"")
        resp.headers = {"Content-Type": "application/json"}

        assert is_problem_details_response(resp) is False

    def test_does_not_detect_without_content_type(self) -> None:
        resp = MockResponse(b"")
        resp.headers = {}

        assert is_problem_details_response(resp) is False

class TestParseProblemDetails:
    def test_parses_valid_problem_details(self) -> None:
        problem_data = {
            "status": 404,
            "title": "Not Found",
            "detail": "The package 'test-package' was not found",
        }
        resp = MockResponse(json.dumps(problem_data).encode())
        resp.headers = {"Content-Type": "application/problem+json"}
        resp.status_code = 404

        problem = parse_problem_details(resp)
        assert problem is not None
        assert problem.status == 404
        assert problem.title == "Not Found"
        assert problem.detail is not None
        assert "test-package" in problem.detail


    def test_returns_none_for_non_problem_details(self) -> None:
        resp = MockResponse(b"<html>Error</html>")
        resp.headers = {"Content-Type": "text/html"}

        problem = parse_problem_details(resp)
        assert problem is None

    def test_handles_malformed_json(self) -> None:
        resp = MockResponse(b"not valid json")
        resp.headers = {"Content-Type": "application/problem+json"}

        problem = parse_problem_details(resp)
        assert problem is None

@pytest.mark.parametrize(
    "status_code, title, detail",
    [
        (404, "Package Not Found", "The requested package does not exist"),
        (500, "Internal Server Error", "An unexpected error occurred"),
        (403, "Forbidden", "Access denied to this resource"),
    ],
)

class TestRaiseForStatusWithProblemDetails:
    def test_raises_http_problem_details_error(
        self, status_code: int, title: str, detail: str
    ) -> None:
        problem_data = {
            "status": status_code,
            "title": title,
            "detail": detail,
        }
        resp = MockResponse(json.dumps(problem_data).encode())
        resp.status_code = status_code
        resp.headers = {"Content-Type": "application/problem+json"}
        resp.url = "https://pypi.org/simple/some-package/"

        with pytest.raises(HTTPProblemDetailsError) as excinfo:
            raise_for_status(resp)

        assert excinfo.value.problem_details.status == status_code
        assert excinfo.value.problem_details.title == title
        assert excinfo.value.response == resp


@pytest.mark.parametrize(
    "status_code, error_type",
    [
        (404, "Client Error"),
        (500, "Server Error"),
        (403, "Client Error"),
    ],
)

class TestRaiseForStatusBackwardCompatibility:
    def test_raises_network_connection_error(
        self, status_code: int, error_type: str
    ) -> None:
        resp = MockResponse(b"<html>Error</html>")
        resp.status_code = status_code
        resp.headers = {"Content-Type": "text/html"}
        resp.url = "https://pypi.org/simple/nonexistent-package/"
        resp.reason = "Error"

        with pytest.raises(NetworkConnectionError) as excinfo:
            raise_for_status(resp)

        assert f"{status_code} {error_type}" in str(excinfo.value)
        assert excinfo.value.response == resp
