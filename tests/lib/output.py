import threading
from io import StringIO

from pip._internal.cli.terminal import Renderable, Terminal
from pip._internal.utils.compat import override


def render_to_text(
    renderable: str | Renderable,
    *,
    color: bool = False,
) -> str:
    with StringIO() as stream:
        console = Terminal(file=stream, color=color)
        console.print(renderable)
        return stream.getvalue()


class TerminalOutput(StringIO):
    """Capture worker output and wait for actual writes without polling sleeps."""

    def __init__(self) -> None:
        super().__init__()
        self._caller = threading.current_thread()
        self._condition = threading.Condition()
        self.background_writes: list[tuple[threading.Thread, str]] = []

    @override
    def write(self, text: str) -> int:
        with self._condition:
            result = super().write(text)
            worker = threading.current_thread()
            if worker is not self._caller:
                self.background_writes.append((worker, text))
                self._condition.notify_all()
            return result

    def wait_for_background_write(self, prefix: str = "", *, after: int = 0) -> None:
        with self._condition:
            assert self._condition.wait_for(
                lambda: any(
                    text.startswith(prefix)
                    for _, text in self.background_writes[after:]
                ),
                timeout=5,
            ), "animation did not repaint while the caller waited"

    def assert_workers_stopped(self) -> None:
        assert self.background_writes, "no worker wrote output"
        assert all(not worker.is_alive() for worker, _ in self.background_writes)
