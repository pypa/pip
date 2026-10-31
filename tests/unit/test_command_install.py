import errno
import functools
import importlib
import importlib.util
import os
import subprocess
import sys
from cmd import Cmd
from collections.abc import Callable, Iterator
from importlib.machinery import ExtensionFileLoader, PathFinder
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

from pip._vendor.requests.exceptions import InvalidProxyURL

from pip._internal.commands import install
from pip._internal.commands.install import (
    _prevent_further_imports,
    create_os_error_message,
    decide_user_install,
)
from pip._internal.locations import get_scheme
from pip._internal.utils.temp_dir import TempDirectory


def test_target_upgrade_preserves_parent(tmp_path: Path) -> None:
    staged = TempDirectory(path=str(tmp_path / "staged"))
    source = Path(get_scheme("", home=staged.path).purelib) / "probe.py"
    source.parent.mkdir(parents=True)
    source.write_text("replacement\n")
    target = tmp_path / "target"
    target.mkdir()
    target.chmod(0o750)
    original_stat = target.stat()
    (target / "probe.py").write_text("original\n")

    install.InstallCommand("install", "")._handle_target_dir(
        str(target), staged, upgrade=True
    )

    assert (target / "probe.py").read_text() == "replacement\n"
    assert target.stat().st_ino == original_stat.st_ino
    assert target.stat().st_mode == original_stat.st_mode


@pytest.mark.skipif("sys.platform == 'win32'")
def test_target_upgrade_preserves_dangling_symlink(tmp_path: Path) -> None:
    staged = TempDirectory(path=str(tmp_path / "staged"))
    source = Path(get_scheme("", home=staged.path).purelib) / "probe"
    source.mkdir(parents=True)
    target = tmp_path / "target"
    target.mkdir()
    link = target / "probe"
    link.symlink_to("missing", target_is_directory=True)

    install.InstallCommand("install", "")._handle_target_dir(
        str(target), staged, upgrade=True
    )

    assert link.is_symlink()
    assert os.readlink(link) == "missing"
    assert source.is_dir()


class TestDecideUserInstall:
    @mock.patch("site.ENABLE_USER_SITE", True)
    @mock.patch("pip._internal.commands.install.site_packages_writable")
    def test_prefix_and_target(self, sp_writable: mock.Mock) -> None:
        sp_writable.return_value = False

        assert decide_user_install(use_user_site=None, prefix_path="foo") is False

        assert decide_user_install(use_user_site=None, target_dir="bar") is False

    @pytest.mark.parametrize(
        "enable_user_site,site_packages_writable,result",
        [
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_most_cases(
        self,
        enable_user_site: bool,
        site_packages_writable: bool,
        result: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("site.ENABLE_USER_SITE", enable_user_site)
        monkeypatch.setattr(
            "pip._internal.commands.install.site_packages_writable",
            lambda **kw: site_packages_writable,
        )
        assert decide_user_install(use_user_site=None) is result


@pytest.mark.parametrize(
    "error, show_traceback, using_user_site, expected",
    [
        # show_traceback = True, using_user_site = True
        (
            OSError("Illegal byte sequence"),
            True,
            True,
            "Could not install packages due to an OSError.\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            True,
            True,
            "Could not install packages due to an OSError.\nCheck the permissions.\n",
        ),
        # show_traceback = True, using_user_site = False
        (
            OSError("Illegal byte sequence"),
            True,
            False,
            "Could not install packages due to an OSError.\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            True,
            False,
            "Could"
            " not install packages due to an OSError.\nConsider using the"
            " `--user` option or check the permissions.\n",
        ),
        # show_traceback = False, using_user_site = True
        (
            OSError("Illegal byte sequence"),
            False,
            True,
            "Could not install packages due to an OSError: Illegal byte sequence\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            False,
            True,
            "Could"
            " not install packages due to an OSError: [Errno 13] No file"
            " permission\nCheck the permissions.\n",
        ),
        # show_traceback = False, using_user_site = False
        (
            OSError("Illegal byte sequence"),
            False,
            False,
            "Could not install packages due to an OSError: Illegal byte sequence\n",
        ),
        (
            OSError(errno.EACCES, "No file permission"),
            False,
            False,
            "Could not install packages due to an OSError: [Errno 13] No"
            " file permission\nConsider using the `--user` option or check the"
            " permissions.\n",
        ),
        # Testing custom InvalidProxyURL with help message
        #  show_traceback = True, using_user_site = True
        (
            InvalidProxyURL(),
            True,
            True,
            "Could not install packages due to an OSError.\n"
            "Consider checking your local proxy configuration"
            ' with "pip config debug".\n',
        ),
        # Testing both long path error (ENOENT)
        # and long file/folder name error (EINVAL) on Windows
        pytest.param(
            OSError(errno.ENOENT, "No such file or directory", f"C:{'/a' * 261}"),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 2] No such file or directory: 'C:{'/a' * 261}'\n"
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
        pytest.param(
            OSError(errno.EINVAL, "No such file or directory", f"C:/{'a' * 256}"),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 22] No such file or directory: 'C:/{'a' * 256}'\n"
            "HINT: This error might be caused by a file or folder name exceeding "
            "255 characters, which is a Windows limitation even if long paths "
            "are enabled.\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
        pytest.param(
            OSError(
                errno.EINVAL, "No such file or directory", f"C:{'/a' * 261}/{'b' * 256}"
            ),
            False,
            False,
            "Could not install packages due to an OSError: "
            f"[Errno 22] No such file or directory: 'C:{'/a' * 261}/{'b' * 256}'\n"
            "HINT: This error might be caused by a file or folder name exceeding "
            "255 characters, which is a Windows limitation even if long paths "
            "are enabled.\n "
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows-specific filename length test"
            ),
        ),
    ],
)
def test_create_os_error_message(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
    show_traceback: bool,
    using_user_site: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(install, "running_under_virtualenv", lambda: False)
    msg = create_os_error_message(error, show_traceback, using_user_site)
    assert msg == expected


def test_prevent_further_imports_blocks_import(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Nested installations share one hook and return to warnings when all finish."""
    monkeypatch.setattr(install, "_IMPORT_AUDIT_HOOK_INSTALLED", False)
    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", set())
    monkeypatch.setattr(install, "_WARNED_IMPORTS", set())
    monkeypatch.setattr(sys, "meta_path", sys.meta_path.copy())

    add_hook = mock.Mock()
    monkeypatch.setattr(sys, "addaudithook", add_hook)

    with _prevent_further_imports():
        with _prevent_further_imports():
            pass

        for module in ("unknown_module", "os", "encodings.iso8859_15"):
            with pytest.raises(install.BlockedImportError, match=module):
                install._prevent_import_hook("import", (module,))
        install._prevent_import_hook("open", ("unknown_module",))

    assert not install._ACTIVE_INSTALLATIONS
    for _ in range(2):
        install._prevent_import_hook("import", ("after_install",))
    assert len(caplog.records) == 1
    assert "Unsafe import" in caplog.text
    assert "all required modules before running pip install" in caplog.text
    assert (
        "https://pip.pypa.io/en/stable/user_guide/#using-pip-from-your-program"
        in caplog.text
    )

    with _prevent_further_imports():
        with pytest.raises(install.BlockedImportError, match="after_install"):
            install._prevent_import_hook("import", ("after_install",))

    add_hook.assert_called_once_with(install._prevent_import_hook)
    assert sys.meta_path[0] is install._IMPORT_BLOCKER
    assert sum(finder is install._IMPORT_BLOCKER for finder in sys.meta_path) == 1


def test_import_blocker_preserves_other_finders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Move only the owned blocker, without comparing third-party finders."""

    def reject_equality(self: object, other: object) -> bool:
        raise AssertionError("Finder equality must not be called")

    finder_type = type("Finder", (PathFinder,), {"__eq__": reject_equality})
    first, second = finder_type(), finder_type()
    blocker = install._IMPORT_BLOCKER
    meta_path = [first, blocker, second, blocker]
    monkeypatch.setattr(sys, "meta_path", meta_path)
    monkeypatch.setattr(install, "_IMPORT_AUDIT_HOOK_INSTALLED", True)
    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", set())

    for _ in range(2):
        with _prevent_further_imports():
            assert sys.meta_path is meta_path
            assert tuple(map(id, sys.meta_path)) == (id(blocker), id(first), id(second))


def test_post_install_warning_allows_logging_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reentrant or failing logging handler must not prevent a caller's import."""
    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", set())
    monkeypatch.setattr(install, "_WARNED_IMPORTS", set())

    def warning(*args: object) -> None:
        install._prevent_import_hook("import", ("handler_module",))
        raise RuntimeError("The caller's logging handler failed")

    with mock.patch.object(install.logger, "warning", side_effect=warning) as log:
        install._prevent_import_hook("import", ("handler_module",))

    log.assert_called_once()


@pytest.mark.parametrize("unicode_version", ["4.1.0", "latest"])
def test_progress_rendering_after_import_guard(
    monkeypatch: pytest.MonkeyPatch, unicode_version: str
) -> None:
    monkeypatch.setenv("UNICODE_VERSION", unicode_version)
    script = (
        Path(__file__).resolve().parents[1] / "lib" / "check_installation_imports.py"
    )
    subprocess.run([sys.executable, str(script), "progress"], check=True)


def test_netrc_authentication_after_import_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine example.com login username password secret\n")
    netrc_file.chmod(0o600)
    monkeypatch.setenv("NETRC", str(netrc_file))
    script = (
        Path(__file__).resolve().parents[1] / "lib" / "check_installation_imports.py"
    )
    subprocess.run([sys.executable, str(script), "netrc"], check=True)


@pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="Checks CPython's native import audit events",
)
def test_native_extension_loader_is_blocked() -> None:
    spec = importlib.util.find_spec("_sqlite3")
    if spec is None or not isinstance(spec.loader, ExtensionFileLoader):
        pytest.skip("A shared extension module is required")

    script = (
        Path(__file__).resolve().parents[1] / "lib" / "check_installation_imports.py"
    )
    subprocess.run([sys.executable, str(script), "extension"], check=True)


def test_importlib_preserves_eager_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = "_pip_unavailable_backend"
    monkeypatch.setattr(install, "_IMPORT_ERRORS", {})
    install._eagerly_import_modules((name,))
    original = install._IMPORT_ERRORS[name]

    monkeypatch.setattr(sys, "meta_path", [install._ImportBlocker(), *sys.meta_path])
    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", {object()})
    with pytest.raises(ModuleNotFoundError) as caught:
        importlib.import_module(name)

    assert caught.value is original


def test_command_loop_without_readline_after_import_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep cmd's optional-readline fallback working after installation."""
    monkeypatch.setattr(install, "_IMPORT_ERRORS", {})
    monkeypatch.setitem(sys.modules, "readline", None)
    install._eagerly_import_modules(install._INTERNAL_EAGER_IMPORTS)
    monkeypatch.delitem(sys.modules, "readline")

    class ExitCommand(Cmd):
        def do_exit(self, arg: str) -> bool:
            return True

    command = ExitCommand(stdout=StringIO())
    command.cmdqueue.append("exit")
    monkeypatch.setattr(sys, "meta_path", [install._ImportBlocker(), *sys.meta_path])
    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", {object()})

    command.cmdloop()

    assert "readline" not in sys.modules


@pytest.mark.parametrize(
    "error",
    [
        ImportError("Optional backend unavailable"),
        ModuleNotFoundError("Missing dependency", name="backend_dependency"),
    ],
)
def test_eager_import_errors_are_preserved(
    monkeypatch: pytest.MonkeyPatch, error: ImportError
) -> None:
    """Reuse the original optional-import error across repeated guarded attempts."""
    monkeypatch.setattr(install, "_IMPORT_ERRORS", {"previous_backend": error})
    importer = mock.Mock(side_effect=error)
    monkeypatch.setattr(install, "__import__", importer, raising=False)

    install._eagerly_import_modules(("optional_backend", "optional_backend"))
    assert "previous_backend" not in install._IMPORT_ERRORS

    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", {object()})

    for _ in range(2):
        with pytest.raises(type(error)) as caught:
            install._prevent_import_hook("import", ("optional_backend",))
        assert caught.value is error

    importer.assert_called_once_with("optional_backend")

    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", set())
    install._prevent_import_hook("import", ("optional_backend",))


@pytest.fixture
def lazy_import_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[ModuleType]:
    """Isolate installation dependencies with real lazy bindings on Python 3.15+."""
    if sys.version_info < (3, 15):
        pytest.skip("Lazy imports require Python 3.15")

    owner = ModuleType("_pip_reify_owner")
    monkeypatch.setitem(sys.modules, owner.__name__, owner)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(install, "_IMPORT_ERRORS", {})
    try:
        yield owner
    finally:
        for name in tuple(sys.modules):
            if name.startswith("_pip_reify_") and name != owner.__name__:
                del sys.modules[name]
        sys.lazy_modules.difference_update(
            name for name in tuple(sys.lazy_modules) if name.startswith("_pip_reify_")
        )


def test_import_preloading_does_not_invoke_callable_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def module_name(instance: object) -> str:
        raise AssertionError("Callable module descriptor invoked")

    def call(instance: object) -> None:
        pass

    # Use a real descriptor to check static attribute access.
    callable_type = type(
        "CallableWithDescriptor",
        (),
        {"__module__": property(module_name), "__call__": call},
    )

    class PartialWithDescriptor(functools.partial[object]):
        __module__ = "_pip_reify_unloaded"

        @property
        def func(self) -> Callable[..., object]:
            raise AssertionError("Partial function descriptor invoked")

    owner = ModuleType("_pip_reify_owner")
    owner.__dict__["value"] = callable_type()
    owner.__dict__["partial"] = PartialWithDescriptor(call)
    monkeypatch.setitem(sys.modules, owner.__name__, owner)

    assert list(install._referenced_modules(owner)) == []
    install._reify_lazy_imports((owner.__name__,))


@pytest.mark.parametrize(
    "definition",
    [
        "def value():\n    return _pip_reify_second.value\n",
        "class value:\n"
        "    def __call__(self):\n"
        "        return _pip_reify_second.value\n",
        "class Meta(type):\n"
        "    @property\n"
        "    def __dict__(cls):\n"
        "        raise AssertionError('Metaclass descriptor invoked')\n"
        "class value(metaclass=Meta):\n"
        "    def __call__(self):\n"
        "        return _pip_reify_second.value\n",
        "from functools import lru_cache\n"
        "@lru_cache\n"
        "def value():\n"
        "    return _pip_reify_second.value\n",
        "from contextlib import contextmanager\n"
        "@contextmanager\n"
        "def value():\n"
        "    yield _pip_reify_second.value\n",
        "class Service:\n"
        "    def value(self):\n"
        "        return _pip_reify_second.value\n"
        "value = Service().value\n",
        "from functools import partial\n"
        "def callback():\n"
        "    return _pip_reify_second.value\n"
        "inner = partial(callback)\n"
        "inner.label = 'callback'\n"
        "value = partial(inner)\n",
        "from functools import partialmethod\n"
        "class Service:\n"
        "    def callback(self):\n"
        "        return _pip_reify_second.value\n"
        "    value = partialmethod(callback)\n"
        "value = Service().value\n",
        "from functools import partial\n"
        "class Service:\n"
        "    def callback(cls):\n"
        "        return _pip_reify_second.value\n"
        "    value = classmethod(partial(callback))\n"
        "value = Service.value\n",
    ],
    ids=[
        "function",
        "class",
        "metaclass",
        "cached-function",
        "context-manager",
        "bound-method",
        "nested-partial",
        "partial-method",
        "class-partial",
    ],
)
@pytest.mark.parametrize(
    "statement, preloaded",
    [
        ("lazy import _pip_reify_first as alias", False),
        ("lazy from _pip_reify_first import value as alias", False),
        ("lazy import _pip_reify_first as alias", True),
        ("lazy from _pip_reify_first import value as alias", True),
    ],
)
def test_reify_lazy_imports_loads_transitive_targets(
    lazy_import_owner: ModuleType,
    tmp_path: Path,
    statement: str,
    preloaded: bool,
    definition: str,
) -> None:
    """Resolve module and attribute bindings, including already-loaded targets."""
    (tmp_path / "_pip_reify_first.py").write_text(
        "lazy import _pip_reify_second\n" + definition
    )
    (tmp_path / "_pip_reify_second.py").write_text("value = 43\n")

    if preloaded:
        __import__("_pip_reify_first")
    exec(statement, lazy_import_owner.__dict__)
    assert ("_pip_reify_first" in sys.modules) == preloaded

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert "_pip_reify_first" in sys.modules
    assert "_pip_reify_second" in sys.modules
    assert not install._IMPORT_ERRORS


def test_reify_lazy_imports_revisits_existing_owner(
    lazy_import_owner: ModuleType, tmp_path: Path
) -> None:
    """A resolved import can add a lazy binding to an owner already scanned."""
    (tmp_path / "_pip_reify_first.py").write_text(
        'import sys\nexec("lazy import _pip_reify_second", '
        'sys.modules["_pip_reify_owner"].__dict__)\n'
    )
    (tmp_path / "_pip_reify_second.py").write_text("value = 42\n")
    exec("lazy import _pip_reify_first", lazy_import_owner.__dict__)

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert "_pip_reify_second" in sys.modules


def test_reify_lazy_imports_resolves_exported_attributes(
    lazy_import_owner: ModuleType, tmp_path: Path
) -> None:
    """Follow dependencies imported by a module's dynamic attribute export."""
    source = tmp_path / "_pip_reify_exports.py"
    source.write_text(
        "def __getattr__(name):\n"
        '    if name == "exported":\n'
        "        import _pip_reify_dependency\n"
        "        return _pip_reify_dependency\n"
        "    raise AttributeError(name)\n"
    )
    (tmp_path / "_pip_reify_dependency.py").write_text("value = 42\n")
    exec(
        "lazy from _pip_reify_exports import exported as alias",
        lazy_import_owner.__dict__,
    )

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert "_pip_reify_dependency" in sys.modules
    assert not install._IMPORT_ERRORS


def test_reify_lazy_imports_leaves_unrelated_targets_lazy(
    lazy_import_owner: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Limit eager resolution to registered owners and their dependencies."""
    unrelated = ModuleType("_pip_reify_unrelated")
    monkeypatch.setitem(sys.modules, unrelated.__name__, unrelated)
    marker = tmp_path / "unrelated-imported"
    (tmp_path / "_pip_reify_unneeded.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        'raise AssertionError("Unrelated lazy import executed")\n'
    )
    exec("lazy import _pip_reify_unneeded", unrelated.__dict__)

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert not marker.exists()
    assert "_pip_reify_unneeded" not in sys.modules


def test_reify_lazy_imports_ignores_unavailable_eager_module(
    lazy_import_owner: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = "_pip_reify_disabled"
    # None in sys.modules explicitly disables an optional module.
    monkeypatch.setitem(sys.modules, name, None)
    install._eagerly_import_modules((name,))
    install._reify_lazy_imports((name,))

    assert isinstance(install._IMPORT_ERRORS[name], ModuleNotFoundError)


@pytest.mark.parametrize(
    "exception, named",
    [("ImportError", True), ("ImportError", False), ("RuntimeError", False)],
)
def test_reify_lazy_imports_attempts_failed_targets_once(
    lazy_import_owner: ModuleType,
    tmp_path: Path,
    exception: str,
    named: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed optional imports must not be retried or resolve their lazy children."""
    attempts: list[int] = []
    lazy_import_owner.__dict__["attempts"] = attempts
    arguments = (
        "'optional dependency unavailable', name='_pip_reify_failure'"
        if named
        else "'optional dependency unavailable'"
    )
    (tmp_path / "_pip_reify_failure.py").write_text(
        "import _pip_reify_owner\n"
        "_pip_reify_owner.attempts.append(1)\n"
        "lazy import _pip_reify_second\n"
        f"raise {exception}({arguments})\n"
    )
    (tmp_path / "_pip_reify_second.py").write_text("value = 42\n")
    exec("lazy import _pip_reify_failure", lazy_import_owner.__dict__)

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert attempts == [1]
    assert "_pip_reify_second" not in sys.modules
    assert ("_pip_reify_failure" in install._IMPORT_ERRORS) == (
        exception == "ImportError"
    )

    if exception == "ImportError":
        monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", {object()})
        with pytest.raises(ImportError) as cached:
            install._prevent_import_hook("import", ("_pip_reify_failure",))
        assert type(cached.value) is ImportError
        assert str(cached.value) == "optional dependency unavailable"


@pytest.mark.parametrize(
    "module", ["_pip_reify_failure", "_pip_reify_missing_dependency"]
)
def test_reify_lazy_imports_preserves_dependency_import_error(
    lazy_import_owner: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: str,
) -> None:
    """Preserve an optional backend's error when either module is retried."""
    name = "_pip_reify_failure"
    source = tmp_path / f"{name}.py"
    source.write_text("import _pip_reify_missing_dependency\n")
    exec(f"lazy import {name} as dependency", lazy_import_owner.__dict__)

    install._reify_lazy_imports((lazy_import_owner.__name__,))

    assert "_pip_reify_missing_dependency" in install._IMPORT_ERRORS

    monkeypatch.setattr(install, "_ACTIVE_INSTALLATIONS", {object()})
    with pytest.raises(ModuleNotFoundError, match="No module named") as missing:
        install._prevent_import_hook("import", (module,))
    assert missing.value.name == "_pip_reify_missing_dependency"
