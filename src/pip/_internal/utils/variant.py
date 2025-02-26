from __future__ import annotations

import logging
from functools import cache
from importlib.metadata import entry_points
from typing import Generator

from variantlib.combination import get_combinations
from variantlib.config import ProviderConfig
from variantlib.meta import VariantDescription

from pip._internal.configuration import Configuration
from pip._internal.exceptions import ConfigurationError, PipError

logger = logging.getLogger(__name__)


def read_provider_priority_from_pip_config() -> dict[str, int]:
    try:
        config = Configuration(isolated=False)
        config.load()

    except PipError:
        logging.exception("Error while reading PIP configuration")
        return {}

    try:
        provider_priority = config.get_value("variantlib.provider_priority")

        if provider_priority is None or not isinstance(provider_priority, str):
            return {}

        return {item: idx for idx, item in enumerate(provider_priority.split(","))}

    except ConfigurationError:
        # the user didn't set a special configuration
        logging.warning("No Variant Provider prioritization was set inside `pip.conf`.")
        return {}


def get_variant_hashes_by_priority(
    provider_priority_dict: dict[str:int] | None = None,
) -> Generator[VariantDescription]:
    logger.info("Discovering plugins...")
    plugins = entry_points().select(group="variantlib.plugins")

    # sorting providers in priority order:
    provider_priority_dict = read_provider_priority_from_pip_config()
    plugins = sorted(
        plugins, key=lambda name: provider_priority_dict.get(name, float("inf"))
    )

    provider_cfgs = []
    for plugin in plugins:
        try:
            logger.info(f"Loading plugin: {plugin.name} - v{plugin.dist.version}")  # noqa: G004

            # Dynamically load the plugin class
            plugin_class = plugin.load()

            # Instantiate the plugin
            plugin_instance = plugin_class()

            # Call the `run` method of the plugin
            provider_cfg = plugin_instance.run()

            if not isinstance(provider_cfg, ProviderConfig):
                logging.error(
                    f"Provider: {plugin.name} returned an unexpected type: "  # noqa: G004
                    f"{type(provider_cfg)} - Expected: `ProviderConfig`. Ignoring..."
                )
                continue

            provider_cfgs.append(provider_cfg)

        except Exception:
            logging.exception("An unknown error happened - Ignoring plugin")

    yield from get_combinations(provider_cfgs) if provider_cfgs else []


@cache
def get_cached_variant_hashes_by_priority() -> list[VariantDescription]:
    variants = list(get_variant_hashes_by_priority())
    logger.info(f"Total Number of Compatible Variants: {len(variants):,}")  # noqa: G004
    return variants
