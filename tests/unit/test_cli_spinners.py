from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from io import StringIO
from unittest.mock import Mock

import pytest

from pip._vendor.rich.console import Console

from pip._internal.cli import spinners
from pip._internal.cli.spinners import open_rich_spinner


@contextmanager
def patch_logger_level(level: int) -> Generator[None]:
    """Patch the spinner logger level temporarily."""
    original_level = spinners.logger.level
    spinners.logger.setLevel(level)
    try:
        yield
    finally:
        spinners.logger.setLevel(original_level)


class TestRichSpinner:
    def test_interactive_output_keeps_finished_line(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class TTY(StringIO):
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(spinners, "get_indentation", lambda: 2)
        stream = TTY()
        with patch_logger_level(logging.INFO):
            with open_rich_spinner(
                "working", Console(file=stream, force_terminal=True)
            ):
                pass

        output = stream.getvalue()
        assert "\x1b[2K  working ... done\n" in output

    def test_non_interactive_output(
        self,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            spinners,
            "sys",
            Mock(stdout=Mock(isatty=Mock(return_value=False))),
        )
        caplog.set_level(logging.INFO, logger=spinners.logger.name)

        with patch_logger_level(logging.INFO):
            with spinners.open_spinner("working"):
                pass

        assert [
            record.getMessage()
            for record in caplog.records
            if record.name == spinners.logger.name
        ] == [
            "working: started",
            "working: finished with status 'done'",
        ]

    @pytest.mark.parametrize(
        "status, func",
        [
            ("done", lambda: None),
            ("error", lambda: 1 / 0),
            ("canceled", Mock(side_effect=KeyboardInterrupt)),
        ],
    )
    def test_finish(self, status: str, func: Callable[[], None]) -> None:
        """
        Check that the spinner finish message is set correctly depending
        on how the spinner came to a stop.
        """
        stream = StringIO()
        try:
            with patch_logger_level(logging.INFO):
                with open_rich_spinner("working", Console(file=stream)):
                    func()
        except BaseException:
            pass

        output = stream.getvalue()
        assert output == f"working ... {status}"

    @pytest.mark.parametrize(
        "level, visible",
        [(logging.ERROR, False), (logging.INFO, True), (logging.DEBUG, True)],
    )
    def test_verbosity(self, level: int, visible: bool) -> None:
        """Is the spinner hidden at the appropriate verbosity?"""
        stream = StringIO()
        with patch_logger_level(level):
            with open_rich_spinner("working", Console(file=stream)):
                pass

        assert bool(stream.getvalue()) == visible
