import importlib
import ssl
import sys
import warnings
from collections.abc import Sequence
from importlib.machinery import ModuleSpec
from types import ModuleType

import pytest

from pip._vendor import requests
from pip._vendor.urllib3 import contrib

from pip._internal.utils import compat


class PyOpenSSLImportBlocker:
    """Record attempts to import an unavailable optional TLS backend."""

    def __init__(self) -> None:
        self.attempted = False

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname == "pip._vendor.urllib3.contrib.pyopenssl":
            self.attempted = True
            raise ImportError("PyOpenSSL is unavailable")
        return None


@pytest.mark.parametrize("windows, expected_attempt", [(False, True), (True, False)])
def test_pyopenssl_fallback_platform(
    monkeypatch: pytest.MonkeyPatch, windows: bool, expected_attempt: bool
) -> None:
    blocker = PyOpenSSLImportBlocker()
    with warnings.catch_warnings():
        try:
            with monkeypatch.context() as patch:
                patch.setattr(compat, "WINDOWS", windows)
                patch.setattr(ssl, "HAS_SNI", False)
                # Cached modules bypass import finders.
                patch.delitem(
                    sys.modules, "pip._vendor.urllib3.contrib.pyopenssl", raising=False
                )
                patch.delattr(contrib, "pyopenssl", raising=False)
                patch.setattr(sys, "meta_path", [blocker, *sys.meta_path])

                importlib.reload(requests)

                assert blocker.attempted is expected_attempt
        finally:
            importlib.reload(requests)
