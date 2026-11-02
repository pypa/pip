"""Check dynamic imports against the real installation guard."""

import importlib
import importlib.metadata
import importlib.util
import sys
from collections.abc import Callable, Sequence
from importlib.machinery import ExtensionFileLoader, ModuleSpec, PathFinder
from io import StringIO
from pathlib import Path
from types import ModuleType

import pip._vendor

if sys.argv[-1] == "debundled":
    pip._vendor.vendored("pygments")
    for module in (
        "rich",
        "rich.console",
        "rich.highlighter",
        "rich.logging",
        "rich.markup",
        "rich.progress",
        "rich.segment",
        "rich.style",
        "rich.text",
        "rich.traceback",
    ):
        pip._vendor.vendored(module)
    assert sys.modules["pip._vendor.pygments"] is sys.modules["pygments"]
    assert sys.modules["pip._vendor.rich"] is sys.modules["rich"]


def main() -> None:
    """Check a fresh module import, then repeat it after the module is cached."""
    # Select the external namespaces before importing installation dependencies.
    from pip._vendor.pygments.plugin import (
        find_plugin_filters,
        find_plugin_formatters,
        find_plugin_lexers,
        find_plugin_styles,
        iter_entry_points,
    )

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
        name="guarded", group="pygments.lexers", value="guarded_import_plugin:VALUE"
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
        "lexer": ("guarded_import_plugin", lambda: list(find_plugin_lexers())),
        "formatter": ("guarded_import_plugin", lambda: list(find_plugin_formatters())),
        "style": ("guarded_import_plugin", lambda: list(find_plugin_styles())),
        "filter": ("guarded_import_plugin", lambda: list(find_plugin_filters())),
    }
    module_name, load = imports[kind]
    groups = {
        "lexer": "lexers",
        "formatter": "formatters",
        "style": "styles",
        "filter": "filters",
    }
    if kind in groups:
        # Discover metadata before blocking, keeping only the plugin module cold.
        iter_entry_points(f"pygments.{groups[kind]}")
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
    elif kind in {"lexer", "entrypoint"}:
        assert loaded == ([42] if kind == "lexer" else 42)
    else:
        assert loaded == [("guarded", 42)]


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
    """Render emoji and non-ASCII text without loading data during installation."""
    from pip._vendor import rich
    from pip._vendor.rich.console import Console
    from pip._vendor.rich.progress import Progress, TextColumn

    from pip._internal.commands.install import (
        _INTERNAL_EAGER_IMPORTS,
        _eagerly_import_modules,
        _prevent_further_imports,
    )

    output = StringIO()
    _eagerly_import_modules(_INTERNAL_EAGER_IMPORTS)
    loaded_modules = set(sys.modules)

    with _prevent_further_imports():
        console = Console(
            file=output,
            force_terminal=True,
            legacy_windows=False,
            color_system=None,
            width=40,
        )
        with Progress(
            TextColumn("{task.description}"),
            console=console,
            auto_refresh=False,
        ) as progress:
            task = progress.add_task(":package: café", total=1)
            progress.update(task, completed=1)

    late_rich_imports = {
        name
        for name in sys.modules.keys() - loaded_modules
        if name.startswith(f"{rich.__name__}.")
    }
    assert not late_rich_imports, late_rich_imports
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
