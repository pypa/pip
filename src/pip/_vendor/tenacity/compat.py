"""Utilities for providing backward compatibility."""

import inspect
from fractions import Fraction
from warnings import warn

import six

from tenacity import _utils


def warn_about_non_retry_state_deprecation(cbname, func, stacklevel):
    msg = (
        '"%s" function must accept single "retry_state" parameter,'
        ' please update %s' % (cbname, _utils.get_callback_name(func)))
    warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)


def warn_about_dunder_non_retry_state_deprecation(fn, stacklevel):
    msg = (
        '"%s" method must be called with'
        ' single "retry_state" parameter' % (_utils.get_callback_name(fn)))
    warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)


def func_takes_retry_state(func):
    if not six.callable(func):
        raise Exception(func)
        return False
    if not inspect.isfunction(func) and not inspect.ismethod(func):
        # func is a callable object rather than a function/method
        func = func.__call__
    func_spec = _utils.getargspec(func)
    return 'retry_state' in func_spec.args


_unset = object()


def _make_unset_exception(func_name, **kwargs):
    missing = []
    for k, v in six.iteritems(kwargs):
        if v is _unset:
            missing.append(k)
    missing_str = ', '.join(repr(s) for s in missing)
    return TypeError(func_name + ' func missing parameters: ' + missing_str)


def _set_delay_since_start(retry_state, delay):
    # Ensure outcome_timestamp - start_time is *exactly* equal to the delay to
    # avoid complexity in test code.
    retry_state.start_time = Fraction(retry_state.start_time)
    retry_state.outcome_timestamp = (retry_state.start_time + Fraction(delay))
    assert retry_state.seconds_since_start == delay


def make_retry_state(previous_attempt_number, delay_since_first_attempt,
                     last_result=None):
    """Construct RetryCallState for given attempt number & delay.

    Only used in testing and thus is extra careful about timestamp arithmetics.
    """
    required_parameter_unset = (previous_attempt_number is _unset or
                                delay_since_first_attempt is _unset)
    if required_parameter_unset:
        raise _make_unset_exception(
            'wait/stop',
            previous_attempt_number=previous_attempt_number,
            delay_since_first_attempt=delay_since_first_attempt)

    from tenacity import RetryCallState
    retry_state = RetryCallState(None, None, (), {})
    retry_state.attempt_number = previous_attempt_number
    if last_result is not None:
        retry_state.outcome = last_result
    else:
        retry_state.set_result(None)
    _set_delay_since_start(retry_state, delay_since_first_attempt)
    return retry_state


def func_takes_last_result(waiter):
    """Check if function has a "last_result" parameter.

    Needed to provide backward compatibility for wait functions that didn't
    take "last_result" in the beginning.
    """
    if not six.callable(waiter):
        return False
    if not inspect.isfunction(waiter) and not inspect.ismethod(waiter):
        # waiter is a class, check dunder-call rather than dunder-init.
        waiter = waiter.__call__
    waiter_spec = _utils.getargspec(waiter)
    return 'last_result' in waiter_spec.args


def stop_dunder_call_accept_old_params(fn):
    """Decorate cls.__call__ method to accept old "stop" signature."""
    @_utils.wraps(fn)
    def new_fn(self,
               previous_attempt_number=_unset,
               delay_since_first_attempt=_unset,
               retry_state=None):
        if retry_state is None:
            from tenacity import RetryCallState
            retry_state_passed_as_non_kwarg = (
                previous_attempt_number is not _unset and
                isinstance(previous_attempt_number, RetryCallState))
            if retry_state_passed_as_non_kwarg:
                retry_state = previous_attempt_number
            else:
                warn_about_dunder_non_retry_state_deprecation(fn, stacklevel=2)
                retry_state = make_retry_state(
                    previous_attempt_number=previous_attempt_number,
                    delay_since_first_attempt=delay_since_first_attempt)
        return fn(self, retry_state=retry_state)
    return new_fn


def stop_func_accept_retry_state(stop_func):
    """Wrap "stop" function to accept "retry_state" parameter."""
    if not six.callable(stop_func):
        return stop_func

    if func_takes_retry_state(stop_func):
        return stop_func

    @_utils.wraps(stop_func)
    def wrapped_stop_func(retry_state):
        warn_about_non_retry_state_deprecation(
            'stop', stop_func, stacklevel=4)
        return stop_func(
            retry_state.attempt_number,
            retry_state.seconds_since_start,
        )
    return wrapped_stop_func


def wait_dunder_call_accept_old_params(fn):
    """Decorate cls.__call__ method to accept old "wait" signature."""
    @_utils.wraps(fn)
    def new_fn(self,
               previous_attempt_number=_unset,
               delay_since_first_attempt=_unset,
               last_result=None,
               retry_state=None):
        if retry_state is None:
            from tenacity import RetryCallState
            retry_state_passed_as_non_kwarg = (
                previous_attempt_number is not _unset and
                isinstance(previous_attempt_number, RetryCallState))
            if retry_state_passed_as_non_kwarg:
                retry_state = previous_attempt_number
            else:
                warn_about_dunder_non_retry_state_deprecation(fn, stacklevel=2)
                retry_state = make_retry_state(
                    previous_attempt_number=previous_attempt_number,
                    delay_since_first_attempt=delay_since_first_attempt,
                    last_result=last_result)
        return fn(self, retry_state=retry_state)
    return new_fn


def wait_func_accept_retry_state(wait_func):
    """Wrap wait function to accept "retry_state" parameter."""
    if not six.callable(wait_func):
        return wait_func

    if func_takes_retry_state(wait_func):
        return wait_func

    if func_takes_last_result(wait_func):
        @_utils.wraps(wait_func)
        def wrapped_wait_func(retry_state):
            warn_about_non_retry_state_deprecation(
                'wait', wait_func, stacklevel=4)
            return wait_func(
                retry_state.attempt_number,
                retry_state.seconds_since_start,
                last_result=retry_state.outcome,
            )
    else:
        @_utils.wraps(wait_func)
        def wrapped_wait_func(retry_state):
            warn_about_non_retry_state_deprecation(
                'wait', wait_func, stacklevel=4)
            return wait_func(
                retry_state.attempt_number,
                retry_state.seconds_since_start,
            )
    return wrapped_wait_func


def retry_dunder_call_accept_old_params(fn):
    """Decorate cls.__call__ method to accept old "retry" signature."""
    @_utils.wraps(fn)
    def new_fn(self, attempt=_unset, retry_state=None):
        if retry_state is None:
            from tenacity import RetryCallState
            if attempt is _unset:
                raise _make_unset_exception('retry', attempt=attempt)
            retry_state_passed_as_non_kwarg = (
                attempt is not _unset and
                isinstance(attempt, RetryCallState))
            if retry_state_passed_as_non_kwarg:
                retry_state = attempt
            else:
                warn_about_dunder_non_retry_state_deprecation(fn, stacklevel=2)
                retry_state = RetryCallState(None, None, (), {})
                retry_state.outcome = attempt
        return fn(self, retry_state=retry_state)
    return new_fn


def retry_func_accept_retry_state(retry_func):
    """Wrap "retry" function to accept "retry_state" parameter."""
    if not six.callable(retry_func):
        return retry_func

    if func_takes_retry_state(retry_func):
        return retry_func

    @_utils.wraps(retry_func)
    def wrapped_retry_func(retry_state):
        warn_about_non_retry_state_deprecation(
            'retry', retry_func, stacklevel=4)
        return retry_func(retry_state.outcome)
    return wrapped_retry_func


def before_func_accept_retry_state(fn):
    """Wrap "before" function to accept "retry_state"."""
    if not six.callable(fn):
        return fn

    if func_takes_retry_state(fn):
        return fn

    @_utils.wraps(fn)
    def wrapped_before_func(retry_state):
        # func, trial_number, trial_time_taken
        warn_about_non_retry_state_deprecation('before', fn, stacklevel=4)
        return fn(
            retry_state.fn,
            retry_state.attempt_number,
        )
    return wrapped_before_func


def after_func_accept_retry_state(fn):
    """Wrap "after" function to accept "retry_state"."""
    if not six.callable(fn):
        return fn

    if func_takes_retry_state(fn):
        return fn

    @_utils.wraps(fn)
    def wrapped_after_sleep_func(retry_state):
        # func, trial_number, trial_time_taken
        warn_about_non_retry_state_deprecation('after', fn, stacklevel=4)
        return fn(
            retry_state.fn,
            retry_state.attempt_number,
            retry_state.seconds_since_start)
    return wrapped_after_sleep_func


def before_sleep_func_accept_retry_state(fn):
    """Wrap "before_sleep" function to accept "retry_state"."""
    if not six.callable(fn):
        return fn

    if func_takes_retry_state(fn):
        return fn

    @_utils.wraps(fn)
    def wrapped_before_sleep_func(retry_state):
        # retry_object, sleep, last_result
        warn_about_non_retry_state_deprecation(
            'before_sleep', fn, stacklevel=4)
        return fn(
            retry_state.retry_object,
            sleep=getattr(retry_state.next_action, 'sleep'),
            last_result=retry_state.outcome)
    return wrapped_before_sleep_func


def retry_error_callback_accept_retry_state(fn):
    if not six.callable(fn):
        return fn

    if func_takes_retry_state(fn):
        return fn

    @_utils.wraps(fn)
    def wrapped_retry_error_callback(retry_state):
        warn_about_non_retry_state_deprecation(
            'retry_error_callback', fn, stacklevel=4)
        return fn(retry_state.outcome)
    return wrapped_retry_error_callback
