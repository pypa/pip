"""Wheel-related pip exceptions."""

from __future__ import annotations

import operator
import platform
import re
import sys
import sysconfig
from dataclasses import dataclass, field
from typing import Final, Literal

from pip._vendor.packaging.tags import INTERPRETER_SHORT_NAMES, Tag
from pip._vendor.packaging.utils import parse_wheel_filename
from pip._vendor.rich.text import Text

from pip._internal.exceptions._base import DiagnosticPipError, InstallationError


class InvalidWheelFilename(InstallationError):
    """Invalid wheel filename."""


class UnsupportedWheel(InstallationError):
    """Unsupported wheel."""


class InvalidWheel(InstallationError):
    """Invalid (e.g. corrupt) wheel."""

    def __init__(self, location: str, name: str):
        self.location = location
        self.name = name

    def __str__(self) -> str:
        return f"Wheel '{self.name}' located at {self.location} is invalid."


def _re_parse(pattern: str, text: str) -> tuple[str, ...] | None:
    if match := re.match(pattern, text):
        return match.groups()
    return None


def _explain_python_tag(full_tag: Tag) -> str | None:
    """Try to explain Python incompatibilities, if possible.

    Specifically checks Python implementation and version."""
    groups = _re_parse(r"([a-z]+)(\d[\d_]*)", full_tag.interpreter)
    if not groups:
        return None
    impl, version = groups

    # Expand abbreviated implementation name if needed.
    for fullname, abbrev in INTERPRETER_SHORT_NAMES.items():
        if impl == abbrev:
            impl = fullname
            break

    if impl != "python" and impl.lower() != sys.implementation.name.lower():
        return (
            f"Wheel requires a different Python implementation: {impl}"
            f" (current: {sys.implementation.name})"
        )

    # If wheel targets stable or no ABI, then Python version is just a minimum.
    if full_tag.abi in ("abi3", "abi3t", "none"):
        op = operator.gt
        plus = "+"
    else:
        op = operator.ne
        plus = ""

    if impl not in ("python", "cpython"):
        return None

    # Check Python language version.
    sys_major, sys_minor = sys.version_info.major, sys.version_info.minor
    if len(version) == 1 and op(int(version), sys_major):
        return f"Wheel requires Python {version}{plus} (current: {sys_major})"
    elif len(version) > 1:
        version_tuple = (int(version[0]), int(version[1:]))
        if op(version_tuple, sys.version_info[:2]):
            return (
                f"Wheel requires Python {version[0]}.{version[1:]}{plus}"
                f" (current: {sys_major}.{sys_minor})"
            )

    return None


def _explain_abi_tag(tag: str) -> str | None:
    """Try to explain ABI incompatibilities, if possible.

    Specific checks only include free-threading/no free-threading.
    """
    if tag.startswith("cp") and sys.version_info >= (3, 13):
        gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED") or 0
        wheel_free_threading = tag.endswith("t")
        if gil_disabled and not wheel_free_threading:
            return "Wheel only supports non free-threaded Python"
        elif not gil_disabled and wheel_free_threading:
            return "Wheel only supports free-threaded Python"

    return None


@dataclass(frozen=True)
class WindowsTag:
    system: str = field(init=False, default="Windows")
    architecture: str


@dataclass(frozen=True)
class MacOSTag:
    system: str = field(init=False, default="macOS")
    architecture: str
    release: tuple[int, int]


@dataclass(frozen=True)
class LinuxTag:
    system: str = field(init=False, default="Linux")
    libc: Literal["glibc", "musl"]
    libc_version: tuple[int, int]
    architecture: str


@dataclass(frozen=True)
class AndroidTag:
    system: Final = "Android"
    architecture: Final = "#not-implemented"


@dataclass(frozen=True)
class iOSTag:
    system: Final = "iOS"
    architecture: Final = "#not-implemented"


def _parse_platform_tag(
    tag: str,
) -> WindowsTag | MacOSTag | LinuxTag | AndroidTag | iOSTag | None:
    tag = tag.lower()
    if tag.startswith("win_"):
        return WindowsTag(tag.removeprefix("win_"))

    if groups := _re_parse(r"macosx_(\d+)_(\d+)_(.+)", tag):
        major, minor, arch = groups
        return MacOSTag(arch, (int(major), int(minor)))

    if match := re.match(r"manylinux(1|2010|2014)_(.+)", tag):
        glibc_ver, arch = match.groups()
        legacy_mapping = {"1": (2, 5), "2010": (2, 12), "2014": (2, 17)}
        return LinuxTag("glibc", legacy_mapping[glibc_ver], arch)
    if groups := _re_parse(r"manylinux_(\d+)_(\d+)_(.+)", tag):
        major, minor, arch = groups
        return LinuxTag("glibc", (int(major), int(minor)), arch)
    if groups := _re_parse(r"musllinux_(\d+)_(\d+)_(.+)", tag):
        major, minor, arch = groups
        return LinuxTag("musl", (int(major), int(minor)), arch)

    if tag.startswith("ios"):
        return iOSTag()
    if tag.startswith("android"):
        return AndroidTag()

    return None


def _explain_platform_tag(raw_tag: str, supported_tags: frozenset[str]) -> str | None:
    """Try to explain platform incompatibilities, if possible.

    Specific checks currently include OS, architecture, and libc mismatches.
    """
    tag = _parse_platform_tag(raw_tag)
    if tag is None:
        return None  # This is an unknown platform, give up.

    # Standardize around "macOS" as it's more well-known
    current_system = "macOS" if platform.system() == "Darwin" else platform.system()
    if tag.system.lower() != current_system.lower():
        return f"Wheel requires {tag.system}"

    if isinstance(tag, (AndroidTag, iOSTag)):
        # TODO: not implemented yet, these platforms are niche.
        return None

    # HACK: Deduce (most of) what this environment supports by inspecting the
    # supported tags returned by packaging. This is hacky, but it's more reliable
    # than trying to determine the OS version, libc version, etc. ourselves.
    supported_platforms = [_parse_platform_tag(t) for t in supported_tags]
    supported_archs = {p.architecture for p in supported_platforms if p is not None}
    if tag.architecture not in supported_archs:
        msg = f"Wheel architecture is unsupported: {tag.architecture}"
        if len(supported_archs) == 1:
            msg += f" (current: {next(iter(supported_archs))})"
        return msg

    def format_version(version: tuple[int, ...]) -> str:
        return ".".join(map(str, version))

    if isinstance(tag, WindowsTag):
        # Due to Windows' excellent backwards compatibility, this should've been an
        # architecture issue but it wasn't, give up.
        return None
    elif isinstance(tag, MacOSTag):
        current_release = max(
            p.release for p in supported_platforms if isinstance(p, MacOSTag)
        )
        # NOTE: due to the many changes to macOS's versioning scheme, this is imperfect.
        if current_release < tag.release:
            return (
                f"Wheel requires macOS >= {format_version(tag.release)}"
                f" (current: {format_version(current_release)})"
            )
    elif isinstance(tag, LinuxTag):
        sys_libc, _ = platform.libc_ver()
        if tag.libc != sys_libc:
            return f"Wheel requires {tag.libc} (current: {sys_libc})"
        sys_libc_ver = max(
            p.libc_version
            for p in supported_platforms
            if isinstance(p, LinuxTag) and p.libc == sys_libc
        )
        if sys_libc_ver < tag.libc_version:
            return (
                f"Wheel requires {tag.libc} {format_version(tag.libc_version)}+"
                f" (current: {format_version(sys_libc_ver)})"
            )

    return None


def diagnose_incompatible_wheel(
    filename: str, supported_tags: frozenset[Tag]
) -> str | None:
    """Determine reasons why a wheel is incompatible.

    Inspects the wheel's supported tags and applies best-effort heuristics
    to determine specific reasons, focusing on the prominent sources
    of incompatibilities that are feasible to verify.

    Returns None if all efforts fail.
    """

    supported_platforms = frozenset(t.platform for t in supported_tags)
    supported_abis = frozenset(t.abi for t in supported_tags)

    def diagnose_one(tag: Tag) -> str | None:
        """Diagnose why one tag is unsuppported.

        Returns the most important reason even if there are multiple
        incompatibilities, in this order: Platform -> Interpreter -> ABI.
        """
        # Confirm that platform/abi is not supported (to avoid false positives).
        if tag.platform not in supported_platforms:
            if reason := _explain_platform_tag(tag.platform, supported_platforms):
                return reason
            return f"Wheel requires a different platform: {tag.platform}"
        # The interpreter tag is weird because if the stable ABI is in use, then
        # python version is only a baseline.
        if reason := _explain_python_tag(tag):
            return reason
        if tag.abi not in supported_abis:
            if reason := _explain_abi_tag(tag.abi):
                return reason
            return f"Wheel ABI is unsupported: {tag.abi}"
        return None

    _, _, _, tags = parse_wheel_filename(filename)
    if len(tags) > 1:
        # This wheel supports multiple tags, first try to surface the reason
        # common to all tags. If that fails, then just print each tag separately.
        tag_reasons = {t: diagnose_one(t) for t in tags}
        unique_reasons = set(tag_reasons.values())
        if len(unique_reasons) == 1 and unique_reasons != {None}:
            return unique_reasons.pop()

        return (
            "None of the wheel's tags match the current environment:\n  "
            + "\n  ".join(map(str, tags))
        )

    return diagnose_one(next(iter(tags)))


class IncompatibleWheelError(DiagnosticPipError, UnsupportedWheel):
    reference = "incompatible-wheel"

    def __init__(self, wheel_filename: str, reason: str | None) -> None:
        hint = "Run 'pip debug -v' for a list of compatible tags for your system."
        super().__init__(
            message=Text.assemble((wheel_filename, "cyan"), " is incompatible"),
            context=Text(reason) if reason else None,
            hint_stmt=hint,
        )
