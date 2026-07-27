import pytest

from pip._internal.commands import create_command
from pip._internal.exceptions import SSLMissingError


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
