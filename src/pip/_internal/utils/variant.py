from __future__ import annotations

import logging
from functools import cache

from variantlib.platform import get_variant_hashes_by_priority

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


@cache
def get_cached_variant_hashes_by_priority() -> list[str]:
    variants = list(get_variant_hashes_by_priority())
    if variants:
        logger.info(f"Total Number of Compatible Variants: {len(variants):,}")  # noqa: G004
    return variants
