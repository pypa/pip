from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING
import logging

from variantlib.api import get_variant_hashes_by_priority
from variantlib.api import check_variant_supported
from variantlib.dist_metadata import DistMetadata

from pip._internal.metadata import FilesystemWheel, get_wheel_distribution

if TYPE_CHECKING:
    from typing import Callable

    from pip._internal.models.link import Link
    from pip._internal.models.wheel import Wheel

logger = logging.getLogger(__name__)


@dataclass
class VariantJson:
    url: str
    getter: Callable([str], dict)

    def json(self) -> dict:
        logger.info("Fetching %(url)s", {"url": self.url})
        return self.getter(self.url)

    def __hash__(self) -> int:
        return hash(self.url)


def get_variants_json_filename(wheel: Wheel) -> str:
    # these are normalized, but with .replace("_", "-")
    return (
        f"{wheel.name.replace("-", "_")}-{wheel.version.replace("-", "_")}-"
        "variants.json"
    )


@cache
def get_cached_variant_hashes_by_priority(
        variants_json: Optional[VariantJson] = None
        ) -> list[str]:
    if variants_json is None:
        return [None]

    parsed_json = variants_json.json()
    variants = list(get_variant_hashes_by_priority(variants_json=parsed_json))
    if variants:
        logger.info(f"Total Number of Compatible Variants: {len(variants):,}")  # noqa: G004
    return [*variants, None]


def variant_wheel_supported(wheel: Wheel, link: Link) -> bool:
    if wheel.variant_hash is None:
        return True

    if link.scheme != "file":
        raise NotImplementedError

    wheel_dist = get_wheel_distribution(FilesystemWheel(link.file_path), "")
    return check_variant_supported(metadata=DistMetadata(wheel_dist.metadata))
