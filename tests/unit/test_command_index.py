import logging

import pytest

from pip._internal.commands import create_command
from pip._internal.commands.search import print_dist_installation_info
from pip._internal.exceptions import SSLMissingError
from pip._internal.metadata import get_metadata_distribution


def test_index_propagates_diagnostic_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Index command diagnostics should be rendered by the base command wrapper."""
    command = create_command("index")
    options, args = command.parse_args(["versions", "example"])

    def raise_diagnostic(*args: object) -> None:
        raise SSLMissingError("https://example.com/")

    monkeypatch.setattr(command, "handler_map", lambda: {"versions": raise_diagnostic})

    with pytest.raises(SSLMissingError):
        command.run(options, args)


@pytest.mark.parametrize(
    "installed, latest",
    [
        ("1.17.0", "1.17.0"),
        # PEP 440 equality is not string equality.
        ("1.17", "1.17.0"),
    ],
)
def test_print_dist_installation_info_marks_latest(
    caplog: pytest.LogCaptureFixture, installed: str, latest: str
) -> None:
    caplog.set_level(logging.INFO)
    metadata = f"Metadata-Version: 2.1\nName: pkg\nVersion: {installed}\n"
    dist = get_metadata_distribution(
        metadata.encode("utf-8"),
        f"pkg-{installed}-py3-none-any.whl",
        "pkg",
    )

    print_dist_installation_info(latest, dist)

    messages = [record.getMessage() for record in caplog.records]
    assert f"INSTALLED: {installed} (latest)" in messages
    assert not any(message.startswith("LATEST:") for message in messages)


@pytest.mark.parametrize(
    "latest, expected_latest_line",
    [
        ("1.17.0", "LATEST:    1.17.0"),
        (
            "1.18.0rc1",
            "LATEST:    1.18.0rc1 (pre-release; install with `pip install --pre`)",
        ),
    ],
)
def test_print_dist_installation_info_shows_latest_when_outdated(
    caplog: pytest.LogCaptureFixture, latest: str, expected_latest_line: str
) -> None:
    caplog.set_level(logging.INFO)
    metadata = "Metadata-Version: 2.1\nName: pkg\nVersion: 1.16.0\n"
    dist = get_metadata_distribution(
        metadata.encode("utf-8"),
        "pkg-1.16.0-py3-none-any.whl",
        "pkg",
    )

    print_dist_installation_info(latest, dist)

    messages = [record.getMessage() for record in caplog.records]
    assert "INSTALLED: 1.16.0" in messages
    assert expected_latest_line in messages
