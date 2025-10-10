"""RFC 9457 - Problem Details for HTTP APIs

This module provides support for RFC 9457 (Problem Details for HTTP APIs),
a standardized format for describing errors in HTTP APIs.

Reference: https://www.rfc-editor.org/rfc/rfc9457
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pip._vendor.requests.models import Response

logger = logging.getLogger(__name__)

RFC9457_CONTENT_TYPE = "application/problem+json"

@dataclass
class ProblemDetails:
    """Represents an RFC 9457 Problem Details object.

    This class encapsulates the core fields defined in RFC 9457:
    - status: The HTTP status code
    - title: A short, human-readable summary of the problem type
    - detail: A human-readable explanation specific to this occurrence
    """

    status: int | None = None
    title: str | None = None
    detail: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProblemDetails:
        return cls(
            status=data.get("status"),
            title=data.get("title"),
            detail=data.get("detail"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ProblemDetails:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise ValueError("Problem details JSON must be an object")
        return cls.from_dict(data)

    def __str__(self) -> str:
        parts = []

        if self.title:
            parts.append(f"{self.title}")
        if self.status:
            parts.append(f"(Status: {self.status})")
        if self.detail:
            parts.append(f"\n{self.detail}")

        return " ".join(parts) if parts else "Unknown problem"


def is_problem_details_response(response: Response) -> bool:
    content_type = response.headers.get("Content-Type", "")
    return content_type.startswith(RFC9457_CONTENT_TYPE)


def parse_problem_details(response: Response) -> ProblemDetails | None:
    if not is_problem_details_response(response):
        return None

    try:
        body = response.content
        if not body:
            logger.warning("Problem details response has empty body")
            return None

        problem = ProblemDetails.from_json(body.decode("utf-8"))

        if problem.status is None:
            problem.status = response.status_code

        logger.debug("Parsed problem details: status=%s, title=%s", problem.status, problem.title)
        return problem

    except (json.JSONDecodeError, ValueError):
        return None
