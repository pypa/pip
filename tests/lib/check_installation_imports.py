"""Check dynamic imports against the real installation guard."""

import importlib
import importlib.metadata
import importlib.util
import os
import sys
from collections.abc import Callable, Sequence
from importlib.machinery import ExtensionFileLoader, ModuleSpec, PathFinder
from io import StringIO
from pathlib import Path
from types import ModuleType


def main() -> None:
    """Check a fresh module import, then repeat it after the module is cached."""
    from pip._internal.commands import create_command
    from pip._internal.commands.debug import get_module_from_module_name
    from pip._internal.commands.install import _prevent_further_imports
    from pip._internal.exceptions import BlockedImportError

    kind = sys.argv[1]
    if kind == "progress":
        check_progress()
        return
    if kind == "netrc":
        check_netrc_authentication()
        return
    if kind == "extension":
        check_extension_loader()
        return
    if kind == "reload":
        check_reload()
        return

    entrypoint = importlib.metadata.EntryPoint(
        name="guarded", group="pip.tests", value="guarded_import_plugin:VALUE"
    )
    imports: dict[str, tuple[str, Callable[[], object]]] = {
        "importlib": (
            "guarded_import_plugin",
            lambda: importlib.import_module("guarded_import_plugin"),
        ),
        "late_finder": (
            "guarded_import_plugin",
            lambda: importlib.import_module("guarded_import_plugin"),
        ),
        "entrypoint": ("guarded_import_plugin", entrypoint.load),
        "spec": (
            "guarded_import_plugin",
            lambda: importlib.util.find_spec("guarded_import_plugin"),
        ),
        "command": (
            "pip._internal.commands.hash",
            lambda: create_command("hash").name,
        ),
        "vendor": (
            "pip._vendor.distlib",
            lambda: get_module_from_module_name("distlib").__name__,
        ),
        "resource": ("guarded_import_resource", read_resource),
    }
    module_name, load = imports[kind]
    assert importlib.metadata.version("guarded_import_plugin") == "1.0"

    assert module_name not in sys.modules

    calls: list[str] = []

    class TrackingFinder:
        def find_spec(
            self,
            fullname: str,
            path: Sequence[str] | None = None,
            target: ModuleType | None = None,
        ) -> ModuleSpec | None:
            if fullname == module_name:
                calls.append(fullname)
                return PathFinder.find_spec(fullname, path, target)
            return None

    if kind == "late_finder":
        with _prevent_further_imports():
            pass

    finder = TrackingFinder()
    sys.meta_path.insert(0, finder)
    blocked_message = ""
    with _prevent_further_imports():
        # Distribution discovery must not be mistaken for module loading.
        assert importlib.metadata.version("guarded_import_plugin") == "1.0"
        try:
            load()
        except BlockedImportError as error:
            blocked_message = str(error)
        else:
            raise AssertionError(f"Imported {module_name} during installation")

    assert repr(module_name) in blocked_message
    assert module_name not in sys.modules
    assert not calls

    loaded = load()
    assert calls == [module_name]
    sys.meta_path.remove(finder)
    if kind == "spec":
        # A metadata-only lookup is allowed again when installation finishes.
        assert loaded is not None
        __import__(module_name)
    assert module_name in sys.modules

    # Cached imports stay usable during later installations.
    with _prevent_further_imports():
        assert load() == loaded

    if kind == "command":
        assert loaded == "hash"
    elif kind == "vendor":
        assert loaded == module_name
    elif kind == "resource":
        assert loaded == "resource contents"
    elif kind in {"importlib", "late_finder", "spec"}:
        assert loaded is not None
    elif kind == "entrypoint":
        assert loaded == 42


def check_reload() -> None:
    """Refuse replaced source during installation, then allow a caller to reload it."""
    from pip._internal.commands.install import _prevent_further_imports
    from pip._internal.exceptions import BlockedImportError

    module = importlib.import_module("guarded_import_plugin")
    assert module.VALUE == 42
    assert module.__file__ is not None
    Path(module.__file__).write_text("VALUE = 'replacement'\n")

    blocked_message = ""
    with _prevent_further_imports():
        try:
            importlib.reload(module)
        except BlockedImportError as error:
            blocked_message = str(error)
        else:
            raise AssertionError("Reload executed replacement source")
        assert module.VALUE == 42

    assert "'guarded_import_plugin'" in blocked_message
    assert importlib.reload(module) is module
    assert module.VALUE == "replacement"


def check_extension_loader() -> None:
    """Check a cold extension loader outside the finder path."""
    from pip._internal.commands.install import _prevent_further_imports
    from pip._internal.exceptions import BlockedImportError

    spec = importlib.util.find_spec("_sqlite3")
    assert spec is not None
    assert isinstance(spec.loader, ExtensionFileLoader)
    assert "_sqlite3" not in sys.modules

    blocked_message = ""
    with _prevent_further_imports():
        try:
            spec.loader.create_module(spec)
        except BlockedImportError as error:
            blocked_message = str(error)
        else:
            raise AssertionError("Direct extension loading bypassed the guard")
    assert "'_sqlite3'" in blocked_message

    assert spec.loader.create_module(spec) is not None


def check_progress() -> None:
    """Render non-ASCII labels without loading modules during installation."""
    from pip._internal.cli.terminal import LiveLine, StyledText, Terminal
    from pip._internal.commands.install import (
        _INTERNAL_EAGER_IMPORTS,
        _eagerly_import_modules,
        _prevent_further_imports,
    )

    output = StringIO()
    os.environ.update(TERM="xterm", TTY_COMPATIBLE="1", TTY_INTERACTIVE="1")
    terminal = Terminal(output, color=False)
    _eagerly_import_modules(_INTERNAL_EAGER_IMPORTS)

    with _prevent_further_imports():
        with LiveLine(terminal) as line:
            line.update("📦 café")
            terminal.print(StyledText("📦 café"))

    assert "📦 café" in output.getvalue()


def check_netrc_authentication() -> None:
    """Read netrc credentials for the first request after installation starts."""
    from pip._internal.commands.install import (
        _INTERNAL_EAGER_IMPORTS,
        _eagerly_import_modules,
        _prevent_further_imports,
    )
    from pip._internal.network.auth import MultiDomainBasicAuth

    assert "netrc" not in sys.modules
    _eagerly_import_modules(_INTERNAL_EAGER_IMPORTS)
    auth = MultiDomainBasicAuth(prompting=False)

    with _prevent_further_imports():
        credentials = auth._get_new_credentials("https://example.com/simple/")

    assert credentials == ("username", "secret")


def read_resource() -> str:
    from pip._internal.utils.compat import open_text_resource

    with open_text_resource("guarded_import_resource", "resource.txt") as stream:
        return stream.read()


if __name__ == "__main__":
    main()
