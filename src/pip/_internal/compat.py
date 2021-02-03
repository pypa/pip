from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any


def ensure_binary(s, encoding='utf-8', errors='strict'):
    # type: (Any, str, str) -> bytes
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))


def ensure_str(s, encoding='utf-8', errors='strict'):
    # type: (Any, str, str) -> str
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))
