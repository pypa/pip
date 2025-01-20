import random
import sys
from time import perf_counter, sleep
from typing import List, NoReturn, Tuple, Type
from unittest.mock import Mock

import pytest

from pip._internal.utils.retry import retry


def test_retry_no_error() -> None:
    function = Mock(return_value="daylily")
    wrapped = retry(wait=0, stop_after_delay=0.01)(function)
    assert wrapped("eggs", alternative="spam") == "daylily"
    function.assert_called_once_with("eggs", alternative="spam")


def test_retry_no_error_after_retry() -> None:
    raised = False

    def _raise_once() -> str:
        nonlocal raised
        if not raised:
            raised = True
            raise RuntimeError("ham")
        return "daylily"

    function = Mock(wraps=_raise_once)
    wrapped = retry(wait=0, stop_after_delay=0.01)(function)
    assert wrapped() == "daylily"
    assert function.call_count == 2


def test_retry_last_error_is_reraised() -> None:
    errors = []

    def _raise_error() -> NoReturn:
        error = RuntimeError(random.random())
        errors.append(error)
        raise error

    function = Mock(wraps=_raise_error)
    wrapped = retry(wait=0, stop_after_delay=0.01)(function)
    with pytest.raises(RuntimeError) as exc_info:
        wrapped()
    assert exc_info.value is errors[-1]

    assert function.call_count > 1, "expected at least one retry"


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit])
def test_retry_ignores_base_exception(exc: Type[BaseException]) -> None:
    function = Mock(side_effect=exc())
    wrapped = retry(wait=0, stop_after_delay=0.01)(function)
    with pytest.raises(exc):
        wrapped()
    function.assert_called_once()


def create_timestamped_callable(sleep_per_call: float = 0) -> Tuple[Mock, List[float]]:
    timestamps = []

    def _raise_error() -> NoReturn:
        timestamps.append(perf_counter())
        if sleep_per_call:
            sleep(sleep_per_call)
        raise RuntimeError

    return Mock(wraps=_raise_error), timestamps


@pytest.mark.skipif(
    sys.platform == "win32", reason="Too flaky on Windows due to poor timer resolution"
)
@pytest.mark.flaky(reruns=3, reruns_delay=1)
@pytest.mark.parametrize("wait_duration", [0.015, 0.045, 0.15])
def test_retry_wait(wait_duration: float) -> None:
    function, timestamps = create_timestamped_callable()
    wrapped = retry(wait=wait_duration, stop_after_delay=0.1)(function)
    start_time = perf_counter()
    with pytest.raises(RuntimeError):
        wrapped()
    assert len(timestamps) >= 2
    # Just check the first retry, with a margin of 10% to permit for
    # unavoidable variation.
    assert timestamps[1] - start_time >= (wait_duration * 0.9)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Too flaky on Windows due to poor timer resolution"
)
@pytest.mark.flaky(reruns=3, reruns_delay=1)
@pytest.mark.parametrize(
    "call_duration, max_allowed_calls", [(0.01, 11), (0.04, 3), (0.15, 1)]
)
def test_retry_time_limit(call_duration: float, max_allowed_calls: int) -> None:
    function, timestamps = create_timestamped_callable(sleep_per_call=call_duration)
    wrapped = retry(wait=0, stop_after_delay=0.1)(function)

    start_time = perf_counter()
    with pytest.raises(RuntimeError):
        wrapped()
    assert len(timestamps) <= max_allowed_calls
    # Add a margin of 10% to permit for unavoidable variation.
    assert all(t - start_time <= (0.1 * 1.1) for t in timestamps)


def test_retry_method() -> None:
    class MyClass:
        def __init__(self) -> None:
            self.calls = 0

        @retry(wait=0, stop_after_delay=3)
        def method(self, string: str) -> str:
            self.calls += 1
            if self.calls >= 5:
                return string
            raise RuntimeError

    o = MyClass()
    assert o.method("orange") == "orange"
    assert o.calls == 5
