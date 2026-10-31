"""Check codec imports during compilation and after installation returns."""

import codecs
import sys
from typing import Any
from unittest.mock import patch

from pip._internal.cli.main import main as pip_main
from pip._internal.commands import install
from pip._internal.exceptions import BlockedImportError
from pip._internal.req import InstallationResult


def main() -> int:
    calls: list[str] = []

    def search(name: str) -> codecs.CodecInfo | None:
        if name in {"cold_probe", "warm_probe"}:
            calls.append(name)
            return codecs.lookup("utf-8")
        return None

    # Warm one built-in codec and one custom codec before installing.
    codecs.register(search)
    codecs.lookup("warm_probe")
    codecs.lookup("cp874")

    calls.clear()
    original = install.install_given_reqs

    def install_given_reqs(*args: Any, **kwargs: Any) -> list[InstallationResult]:
        installed = original(*args, **kwargs)

        for encoding in ("big5", "cold_probe"):
            try:
                codecs.lookup(encoding)
            except BlockedImportError:
                pass
            else:
                raise AssertionError("Blocked codec was cached as missing")
        assert not calls, calls
        return installed

    with patch.object(install, "install_given_reqs", install_given_reqs):
        status = pip_main(["install", "--compile", "--no-index", sys.argv[1]])

    codecs.lookup("big5")
    codecs.lookup("cold_probe")
    assert calls == ["cold_probe"], calls
    return status


if __name__ == "__main__":
    sys.exit(main())
