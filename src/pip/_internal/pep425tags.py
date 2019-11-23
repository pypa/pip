"""Generate and work with PEP 425 Compatibility Tags."""
from __future__ import absolute_import

import distutils.util
import logging
import platform
import re
import sys

from pip._vendor.packaging.tags import (
    Tag,
    compatible_tags,
    cpython_tags,
    generic_tags,
    interpreter_name,
    interpreter_version,
    mac_platforms,
)

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List, Optional, Tuple

    from pip._vendor.packaging.tags import PythonVersion

logger = logging.getLogger(__name__)

_osx_arch_pat = re.compile(r'(.+)_(\d+)_(\d+)_(.+)')


def version_info_to_nodot(version_info):
    # type: (Tuple[int, ...]) -> str
    # Only use up to the first two numbers.
    return ''.join(map(str, version_info[:2]))


def get_impl_version_info():
    # type: () -> Tuple[int, ...]
    """Return sys.version_info-like tuple for use in decrementing the minor
    version."""
    if interpreter_name() == 'pp':
        # as per https://github.com/pypa/pip/issues/2882
        # attrs exist only on pypy
        return (sys.version_info[0],
                sys.pypy_version_info.major,  # type: ignore
                sys.pypy_version_info.minor)  # type: ignore
    else:
        return sys.version_info[0], sys.version_info[1]


def _is_running_32bit():
    # type: () -> bool
    return sys.maxsize == 2147483647


def get_platform():
    # type: () -> str
    """Return our platform name 'win32', 'linux_x86_64'"""
    if sys.platform == 'darwin':
        # distutils.util.get_platform() returns the release based on the value
        # of MACOSX_DEPLOYMENT_TARGET on which Python was built, which may
        # be significantly older than the user's current machine.
        release, _, machine = platform.mac_ver()
        split_ver = release.split('.')

        if machine == "x86_64" and _is_running_32bit():
            machine = "i386"
        elif machine == "ppc64" and _is_running_32bit():
            machine = "ppc"

        return 'macosx_{}_{}_{}'.format(split_ver[0], split_ver[1], machine)

    # XXX remove distutils dependency
    result = distutils.util.get_platform().replace('.', '_').replace('-', '_')
    if result == "linux_x86_64" and _is_running_32bit():
        # 32 bit Python program (running on a 64 bit Linux): pip should only
        # install and run 32 bit compiled extensions in that case.
        result = "linux_i686"

    return result


def get_all_minor_versions_as_strings(version_info):
    # type: (Tuple[int, ...]) -> List[str]
    versions = []
    major = version_info[:-1]
    # Support all previous minor Python versions.
    for minor in range(version_info[-1], -1, -1):
        versions.append(''.join(map(str, major + (minor,))))
    return versions


def _mac_platforms(arch):
    # type: (str) -> List[str]
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
            '{}_{}'.format(name, arch[len('macosx_'):])
            for arch in mac_platforms(mac_version, actual_arch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _custom_manylinux_platforms(arch):
    # type: (str) -> List[str]
    arches = [arch]
    arch_prefix, arch_sep, arch_suffix = arch.partition('_')
    if arch_prefix == 'manylinux2014':
        # manylinux1/manylinux2010 wheels run on most manylinux2014 systems
        # with the exception of wheels depending on ncurses. PEP 599 states
        # manylinux1/manylinux2010 wheels should be considered
        # manylinux2014 wheels:
        # https://www.python.org/dev/peps/pep-0599/#backwards-compatibility-with-manylinux2010-wheels
        if arch_suffix in {'i686', 'x86_64'}:
            arches.append('manylinux2010' + arch_sep + arch_suffix)
            arches.append('manylinux1' + arch_sep + arch_suffix)
    elif arch_prefix == 'manylinux2010':
        # manylinux1 wheels run on most manylinux2010 systems with the
        # exception of wheels depending on ncurses. PEP 571 states
        # manylinux1 wheels should be considered manylinux2010 wheels:
        # https://www.python.org/dev/peps/pep-0571/#backwards-compatibility-with-manylinux1-wheels
        arches.append('manylinux1' + arch_sep + arch_suffix)
    return arches


def _get_custom_platforms(arch):
    # type: (str) -> List[str]
    arch_prefix, arch_sep, arch_suffix = arch.partition('_')
    if arch.startswith('macosx'):
        arches = _mac_platforms(arch)
    elif arch_prefix in ['manylinux2014', 'manylinux2010']:
        arches = _custom_manylinux_platforms(arch)
    else:
        arches = [arch]
    return arches


def _get_python_version(version):
    # type: (str) -> PythonVersion
    if len(version) > 1:
        return int(version[0]), int(version[1:])
    else:
        return (int(version[0]),)


def _get_custom_interpreter(implementation=None, version=None):
    # type: (Optional[str], Optional[str]) -> str
    if implementation is None:
        implementation = interpreter_name()
    if version is None:
        version = interpreter_version()
    return "{}{}".format(implementation, version)


def get_supported(
    version=None,  # type: Optional[str]
    platform=None,  # type: Optional[str]
    impl=None,  # type: Optional[str]
    abi=None  # type: Optional[str]
):
    # type: (...) -> List[Tag]
    """Return a list of supported tags for each version specified in
    `versions`.

    :param version: a string version, of the form "33" or "32",
        or None. The version will be assumed to support our ABI.
    :param platform: specify the exact platform you want valid
        tags for, or None. If None, use the local system platform.
    :param impl: specify the exact implementation you want valid
        tags for, or None. If None, use the local interpreter impl.
    :param abi: specify the exact abi you want valid
        tags for, or None. If None, use the local interpreter abi.
    """
    supported = []  # type: List[Tag]

    python_version = None  # type: Optional[PythonVersion]
    if version is not None:
        python_version = _get_python_version(version)

    interpreter = _get_custom_interpreter(impl, version)

    abis = None  # type: Optional[List[str]]
    if abi is not None:
        abis = [abi]

    platforms = None  # type: Optional[List[str]]
    if platform is not None:
        platforms = _get_custom_platforms(platform)

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
