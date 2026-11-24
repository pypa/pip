import threading

import pytest

from pip._internal.cli import animation
from pip._internal.cli.animation import BackgroundRefresh, RateLimiter


@pytest.mark.parametrize("draw_seconds", [0.0, 0.04, 0.3])
def test_refresh_frame_deadlines(
    monkeypatch: pytest.MonkeyPatch, draw_seconds: float
) -> None:
    """Charge each callback for its work without drifting or catching up in bursts."""
    now = 0.0
    frames: list[float] = []
    waits: list[float] = []

    def draw() -> None:
        nonlocal now
        frames.append(now)
        now += draw_seconds

    def wait(timeout: float | None = None) -> bool:
        nonlocal now
        assert timeout is not None
        if len(waits) == 4:
            finished.set()
            return True
        waits.append(timeout)
        now += timeout
        return False

    finished = threading.Event()
    monkeypatch.setattr(animation.time, "monotonic", lambda: now)
    refresh = BackgroundRefresh(draw, 0.125, enabled=True, name="test-refresh")
    # Control only the scheduler's wait; the real worker must start and join.
    monkeypatch.setattr(refresh._stopped, "wait", wait)
    with refresh:
        assert finished.wait(5), "worker did not finish its scheduled frames"

    if draw_seconds < 0.125:
        assert frames == pytest.approx([0, 0.125, 0.25, 0.375, 0.5])
    else:
        assert waits[1:] == pytest.approx([0.125] * 3)


def test_limiter_resets_after_callback_and_can_force_final_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10.0
    updates: list[float] = []
    monkeypatch.setattr(animation.time, "monotonic", lambda: now)
    limiter = RateLimiter(5)

    def update() -> None:
        nonlocal now
        updates.append(now)
        now += 2

    limiter(update)
    now = 16
    limiter(update)
    assert updates == [10]

    now = 17
    limiter(update)
    limiter(update, force=True)
    assert updates == [10, 17, 19]


@pytest.mark.parametrize("enabled", [False, True])
def test_callback_refresh_owns_initial_draw_throttling_and_cleanup(
    monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    now = 10.0
    updates: list[float] = []
    monkeypatch.setattr(animation.time, "monotonic", lambda: now)

    with BackgroundRefresh(
        lambda: updates.append(now),
        1,
        enabled=enabled,
        background=False,
        name="test-callback-refresh",
    ) as refresh:
        assert updates == ([10] if enabled else [])
        refresh.refresh()
        now = 11
        refresh.refresh()

    now = 12
    refresh.refresh()
    assert updates == ([10, 11] if enabled else [])


def test_worker_owns_frames_while_foreground_requests_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10.0
    monkeypatch.setattr(animation.time, "monotonic", lambda: now)
    caller = threading.current_thread()
    started = threading.Event()
    release = threading.Event()
    writers: list[threading.Thread] = []

    def draw() -> None:
        writers.append(threading.current_thread())
        if threading.current_thread() is not caller:
            started.set()
            assert release.wait(5), "caller did not release the worker"

    with BackgroundRefresh(draw, 0.01, enabled=True, name="test-refresh") as refresh:
        try:
            assert started.wait(5), "worker did not start"
            now = 11
            refresh.refresh()
            assert len(writers) == 2
            assert writers[0] is caller
            assert writers[1] is not caller
        finally:
            release.set()

    assert not writers[1].is_alive()


@pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")
def test_worker_handles_output_failure() -> None:
    caller = threading.current_thread()
    failed = threading.Event()
    workers: list[threading.Thread] = []

    def draw() -> None:
        if threading.current_thread() is not caller:
            workers.append(threading.current_thread())
            failed.set()
            raise BrokenPipeError

    with BackgroundRefresh(draw, 0.01, enabled=True, name="test-refresh"):
        assert failed.wait(5), "worker did not attempt output"

    assert not workers[0].is_alive()
