import contextlib
import logging
from importlib.metadata import EntryPoints, entry_points
from pathlib import Path
from typing import Iterator, List

from pip._internal.models.plugin import DistInspectorPlugin, Plugin, plugin_from_module

logger = logging.getLogger(__name__)
_loaded_plugins: List[Plugin] = []


def iter_entry_points(group_name: str) -> EntryPoints:
    groups = entry_points()
    if hasattr(groups, "select"):
        # New interface in Python 3.10 and newer versions of the
        # importlib_metadata backport.
        return groups.select(group=group_name)
    else:
        assert hasattr(groups, "get")
        # Older interface, deprecated in Python 3.10 and recent
        # importlib_metadata, but we need it in Python 3.8 and 3.9.
        return groups.get(group_name, [])


def load_plugins() -> None:
    for entrypoint in iter_entry_points(group_name="pip.plugins"):
        try:
            module = entrypoint.load()
        except ModuleNotFoundError:
            logger.warning("Tried to load plugin %s but failed", entrypoint.name)
            continue
        plugin = plugin_from_module(entrypoint.name, module)
        if plugin is not None:
            _loaded_plugins.append(plugin)


@contextlib.contextmanager
def _only_raise_value_error(plugin_name: str) -> Iterator[None]:
    try:
        yield
    except ValueError as e:
        raise ValueError(f"Plugin {plugin_name}: {e}") from e
    except Exception as e:
        logger.warning(
            "Plugin %s raised an unexpected exception type: %s",
            plugin_name,
            {e.__class__.__name__},
        )
        raise ValueError(f"Plugin {plugin_name}: {e}") from e


def plugin_pre_download_hook(url: str, filename: str, digest: str) -> None:
    """Call the pre-download hook of all loaded plugins

    This function should be called right before a distribution is downloaded.
    It will go through all the loaded plugins and call their `pre_download(url)`
    function.
    Only ValueError will be raised. If the plugin (incorrectly) raises another
    exception type, this function will wrap it as a ValueError and log
    a warning.
    """

    for p in _loaded_plugins:
        if not isinstance(p, DistInspectorPlugin):
            continue
        with _only_raise_value_error(p.name):
            p.pre_download(url=url, filename=filename, digest=digest)


def plugin_pre_extract_hook(dist: Path) -> None:
    """Call the pre-extract hook of all loaded plugins

    This function should be called right before a distribution is extracted.
    It will go through all the loaded plugins and call their `pre_extract(dist)`
    function.
    Only ValueError will be raised. If the plugin (incorrectly) raises another
    exception type, this function will wrap it as a ValueError and log
    a warning.
    """

    for p in _loaded_plugins:
        if not isinstance(p, DistInspectorPlugin):
            continue
        with _only_raise_value_error(p.name):
            p.pre_extract(dist)
