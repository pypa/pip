"""Generate and work with PEP 425 Compatibility Tags.
"""
import collections
import functools
import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from pip._vendor.packaging.tags import (
    PythonVersion,
    Tag,
    compatible_tags,
    cpython_tags,
    generic_tags,
    interpreter_name,
    interpreter_version,
    mac_platforms,
)

from pip._internal.utils.glibc import libc_ver, parse_glibc_version

_osx_arch_pat = re.compile(r"(.+)_(\d+)_(\d+)_(.+)")
_LAST_GLIBC_MINOR: Dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


@functools.lru_cache()
def _get_glibc_version() -> Tuple[int, int]:
    _, curr_glibc_ver = libc_ver()
    return parse_glibc_version(curr_glibc_ver)


# From PEP 513, PEP 600
def _is_compatible(name: str, arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux  # noqa
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


def version_info_to_nodot(version_info: Tuple[int, ...]) -> str:
    # Only use up to the first two numbers.
    return "".join(map(str, version_info[:2]))


def _mac_platforms(arch: str) -> List[str]:
    match = _osx_arch_pat.match(arch)
    if match:
        name, major, minor, actual_arch = match.groups()
        mac_version = (int(major), int(minor))
        arches = [
            # Since we have always only checked that the platform starts
            # with "macosx", for backwards-compatibility we extract the
            # actual prefix provided by the user in case they provided
            # something like "macosxcustom_". It may be good to remove
            # this as undocumented or deprecate it in the future.
            "{}_{}".format(name, arch[len("macosx_") :])
            for arch in mac_platforms(mac_version, actual_arch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _manylinux_platforms(arch: str) -> List[str]:
    arches = [arch]
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")

    if arch_prefix == "manylinux":
        arches = []
        *curr_glibc_str, curr_arch = arch_suffix.split("_", 2)
        curr_glibc = _GLibCVersion(*map(int, curr_glibc_str))
        too_old_glibc2 = _GLibCVersion(2, 16)
        if curr_arch in {"x86_64", "i686"}:
            # On x86/i686 also oldest glibc to be supported is (2, 5).
            too_old_glibc2 = _GLibCVersion(2, 4)
        glibc_max_list = [curr_glibc]
        for glibc_major in range(curr_glibc.major - 1, 1, -1):
            glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
            glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(tag, arch, glibc_version):
                    arches.append(tag + arch_sep + curr_arch)
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(legacy_tag, arch, glibc_version):
                        arches.append(legacy_tag + arch_sep + curr_arch)

    elif arch_prefix == "manylinux2014":
        # manylinux1/manylinux2010 wheels run on most manylinux2014 systems
        # with the exception of wheels depending on ncurses. PEP 599 states
        # manylinux1/manylinux2010 wheels should be considered
        # manylinux2014 wheels:
        # https://www.python.org/dev/peps/pep-0599/#backwards-compatibility-with-manylinux2010-wheels
        if arch_suffix in {"i686", "x86_64"}:
            arches.append("manylinux2010" + arch_sep + arch_suffix)
            arches.append("manylinux1" + arch_sep + arch_suffix)
    elif arch_prefix == "manylinux2010":
        # manylinux1 wheels run on most manylinux2010 systems with the
        # exception of wheels depending on ncurses. PEP 571 states
        # manylinux1 wheels should be considered manylinux2010 wheels:
        # https://www.python.org/dev/peps/pep-0571/#backwards-compatibility-with-manylinux1-wheels
        arches.append("manylinux1" + arch_sep + arch_suffix)
    return arches


def _get_custom_platforms(arch: str) -> List[str]:
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")
    if arch.startswith("macosx"):
        arches = _mac_platforms(arch)
    elif arch_prefix.startswith("manylinux"):
        arches = _manylinux_platforms(arch)
    else:
        arches = [arch]
    return arches


def _expand_allowed_platforms(platforms: Optional[List[str]]) -> Optional[List[str]]:
    if not platforms:
        return None

    seen = set()
    result = []

    for p in platforms:
        if p in seen:
            continue
        additions = [c for c in _get_custom_platforms(p) if c not in seen]
        seen.update(additions)
        result.extend(additions)

    return result


def _get_python_version(version: str) -> PythonVersion:
    if len(version) > 1:
        return int(version[0]), int(version[1:])
    else:
        return (int(version[0]),)


def _get_custom_interpreter(
    implementation: Optional[str] = None, version: Optional[str] = None
) -> str:
    if implementation is None:
        implementation = interpreter_name()
    if version is None:
        version = interpreter_version()
    return f"{implementation}{version}"


def get_supported(
    version: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    impl: Optional[str] = None,
    abis: Optional[List[str]] = None,
) -> List[Tag]:
    """Return a list of supported tags for each version specified in
    `versions`.

    :param version: a string version, of the form "33" or "32",
        or None. The version will be assumed to support our ABI.
    :param platform: specify a list of platforms you want valid
        tags for, or None. If None, use the local system platform.
    :param impl: specify the exact implementation you want valid
        tags for, or None. If None, use the local interpreter impl.
    :param abis: specify a list of abis you want valid
        tags for, or None. If None, use the local interpreter abi.
    """
    supported: List[Tag] = []

    python_version: Optional[PythonVersion] = None
    if version is not None:
        python_version = _get_python_version(version)

    interpreter = _get_custom_interpreter(impl, version)

    platforms = _expand_allowed_platforms(platforms)

    is_cpython = (impl or interpreter_name()) == "cp"
    if is_cpython:
        supported.extend(
            cpython_tags(
                python_version=python_version,
                abis=abis,
                platforms=platforms,
            )
        )
    else:
        supported.extend(
            generic_tags(
                interpreter=interpreter,
                abis=abis,
                platforms=platforms,
            )
        )
    supported.extend(
        compatible_tags(
            python_version=python_version,
            interpreter=interpreter,
            platforms=platforms,
        )
    )

    return supported
