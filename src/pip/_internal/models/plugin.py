import abc
import logging
from pathlib import Path
from types import ModuleType
from typing import Optional

logger = logging.getLogger(__name__)

PLUGIN_TYPE_DIST_INSPECTOR = "dist-inspector"
SUPPORTED_PLUGIN_TYPES = [PLUGIN_TYPE_DIST_INSPECTOR]


class Plugin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def plugin_type(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class DistInspectorPlugin(Plugin):
    def __init__(self, name: str, loaded_module: ModuleType):
        assert loaded_module.plugin_type() == PLUGIN_TYPE_DIST_INSPECTOR
        if not hasattr(loaded_module, "pre_download") or not hasattr(
            loaded_module, "pre_extract"
        ):
            raise ValueError(
                f'Plugin "{name}" of type {PLUGIN_TYPE_DIST_INSPECTOR} is'
                "missing pre_download and/or pre_extract definitions"
            )

        self._name = name
        self._module = loaded_module

    def plugin_type(self) -> str:
        return self._module.plugin_type()

    @property
    def name(self) -> str:
        return self._name

    def pre_download(self, url: str, filename: str, digest: str) -> None:
        # contract: `pre_download` raises `ValueError` to terminate
        # the operation that intends to download `filename` from `url`
        # with hash `digest`
        self._module.pre_download(url=url, filename=filename, digest=digest)

    def pre_extract(self, dist: Path) -> None:
        # contract: `pre_extract` raises `ValueError` to terminate
        # the operation that intends to unarchive `dist`
        self._module.pre_extract(dist)


def plugin_from_module(name: str, loaded_module: ModuleType) -> Optional[Plugin]:
    if not hasattr(loaded_module, "plugin_type"):
        logger.warning("Ignoring plugin %s due to missing plugin_type definition", name)
    plugin_type = loaded_module.plugin_type()
    if plugin_type not in SUPPORTED_PLUGIN_TYPES:
        logger.warning(
            "Ignoring plugin %s due to unknown plugin type: %s", name, plugin_type
        )

    if plugin_type == PLUGIN_TYPE_DIST_INSPECTOR:
        try:
            return DistInspectorPlugin(name, loaded_module)
        except ValueError as e:
            logger.warning("Ignoring plugin %s due to error: %s", name, e)
    return None
