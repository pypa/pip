import abc
import logging
from pathlib import Path
from types import ModuleType
from typing import List, Optional

logger = logging.getLogger(__name__)

PLUGIN_HOOK_PRE_DOWNLOAD = "pre_download"
PLUGIN_HOOK_PRE_EXTRACT = "pre_extract"
SUPPORTED_PLUGIN_HOOKS = [PLUGIN_HOOK_PRE_DOWNLOAD, PLUGIN_HOOK_PRE_EXTRACT]


class Plugin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def provided_hooks(self) -> List[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class LoadedPlugin(Plugin):
    def __init__(self, name: str, loaded_module: ModuleType):
        self._pre_download = None
        self._pre_extract = None
        if not hasattr(loaded_module, "provided_hooks"):
            raise ValueError(
                f"Ignoring plugin {name} due to missing provided_hooks definition"
            )
        for hook in loaded_module.provided_hooks():
            if hook == PLUGIN_HOOK_PRE_DOWNLOAD:
                if not hasattr(loaded_module, "pre_download"):
                    raise ValueError(
                        f'Plugin "{name}" wants to register a pre-download hook but '
                        "does not define a pre_download method"
                    )
                self._pre_download = loaded_module.pre_download
            elif hook == PLUGIN_HOOK_PRE_EXTRACT:
                if not hasattr(loaded_module, "pre_extract"):
                    raise ValueError(
                        f'Plugin "{name}" wants to register a pre-extract hook but '
                        "does not define a pre_extract method"
                    )
                self._pre_extract = loaded_module.pre_extract
            else:
                raise ValueError(
                    f'Plugin "{name}" wants to register a hook of unknown type:'
                    '"{hook}"'
                )

        self._name = name
        self._module = loaded_module

    def provided_hooks(self) -> List[str]:
        return self._module.provided_hooks()

    @property
    def name(self) -> str:
        return self._name

    def pre_download(self, url: str, filename: str, digest: str) -> None:
        # contract: `pre_download` raises `ValueError` to terminate
        # the operation that intends to download `filename` from `url`
        # with hash `digest`
        if self._pre_download is not None:
            self._pre_download(url=url, filename=filename, digest=digest)

    def pre_extract(self, dist: Path) -> None:
        # contract: `pre_extract` raises `ValueError` to terminate
        # the operation that intends to unarchive `dist`
        if self._pre_extract is not None:
            self._module.pre_extract(dist)


def plugin_from_module(name: str, loaded_module: ModuleType) -> Optional[LoadedPlugin]:
    try:
        return LoadedPlugin(name, loaded_module)
    except ValueError as e:
        logger.warning("Ignoring plugin %s due to error: %s", name, e)
    return None
