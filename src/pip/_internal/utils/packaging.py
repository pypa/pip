import functools
import logging
import re
from typing import Generator, NewType, Optional, Tuple, cast

from pip._vendor.packaging import specifiers, version
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import platform_tags

NormalizedExtra = NewType("NormalizedExtra", str)

logger = logging.getLogger(__name__)

_LEGACY_MANYLINUX_MAP = {
    "manylinux2014": (2, 17),
    "manylinux2010": (2, 12),
    "manylinux1": (2, 5),
}


def check_requires_python(
    requires_python: Optional[str], version_info: Tuple[int, ...]
) -> bool:
    """
    Check if the given Python version matches a "Requires-Python" specifier.

    :param version_info: A 3-tuple of ints representing a Python
        major-minor-micro version to check (e.g. `sys.version_info[:3]`).

    :return: `True` if the given Python version satisfies the requirement.
        Otherwise, return `False`.

    :raises InvalidSpecifier: If `requires_python` has an invalid format.
    """
    if requires_python is None:
        # The package provides no information
        return True
    requires_python_specifier = specifiers.SpecifierSet(requires_python)

    python_version = version.parse(".".join(map(str, version_info)))
    return python_version in requires_python_specifier


@functools.lru_cache(maxsize=512)
def get_requirement(req_string: str) -> Requirement:
    """Construct a packaging.Requirement object with caching"""
    # Parsing requirement strings is expensive, and is also expected to happen
    # with a low diversity of different arguments (at least relative the number
    # constructed). This method adds a cache to requirement object creation to
    # minimize repeated parsing of the same string to construct equivalent
    # Requirement objects.
    return Requirement(req_string)


def safe_extra(extra: str) -> NormalizedExtra:
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.

    This function is duplicated from ``pkg_resources``. Note that this is not
    the same to either ``canonicalize_name`` or ``_egg_link_name``.
    """
    return cast(NormalizedExtra, re.sub("[^A-Za-z0-9.-]+", "_", extra).lower())


def is_pinned(specifier: SpecifierSet) -> bool:
    for sp in specifier:
        if sp.operator == "===":
            return True
        if sp.operator != "==":
            continue
        if sp.version.endswith(".*"):
            continue
        return True
    return False


def filter_manylinux_tags(
    glibc: Tuple[int, int], arch: str
) -> Generator[str, None, None]:
    for tag in filter(lambda t: t.startswith("manylinux"), platform_tags()):
        tag_prefix, _, tag_suffix = tag.partition("_")
        if tag_prefix in _LEGACY_MANYLINUX_MAP:
            tag_glibc = _LEGACY_MANYLINUX_MAP[tag_prefix]
            tag_arch = tag_suffix
        else:
            tag_glibc_major, tag_glibc_minor, tag_arch = tag_suffix.split("_", 2)
            tag_glibc = (int(tag_glibc_major), int(tag_glibc_minor))

        if arch == tag_arch and tag_glibc <= glibc:
            yield tag


def filter_musllinux_tags(
    musl: Tuple[int, int], arch: str
) -> Generator[str, None, None]:
    for tag in filter(lambda t: t.startswith("musllinux"), platform_tags()):
        *_, tag_suffix = tag.partition("_")
        tag_musl_major, tag_musl_minor, tag_arch = tag_suffix.split("_", 2)
        tag_musl = (int(tag_musl_major), int(tag_musl_minor))
        if tag_arch == arch and tag_musl <= musl:
            yield tag
