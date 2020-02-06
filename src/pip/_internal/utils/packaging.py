from pip._vendor.packaging import specifiers, version

from pip._internal.metadata import get_file_lines, get_metadata
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Tuple
    from pip._internal.metadata import Distribution


def check_requires_python(requires_python, version_info):
    # type: (Optional[str], Tuple[int, ...]) -> bool
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

    python_version = version.parse('.'.join(map(str, version_info)))
    return python_version in requires_python_specifier


def get_requires_python(dist):
    # type: (Distribution) -> Optional[str]
    """
    Return the "Requires-Python" metadata for a distribution, or None
    if not present.
    """
    pkg_info_dict = get_metadata(dist)
    requires_python = pkg_info_dict.get('Requires-Python')

    if requires_python is not None:
        # Convert to a str to satisfy the type checker, since requires_python
        # can be a Header object.
        requires_python = str(requires_python)

    return requires_python


def get_installer(dist):
    # type: (Distribution) -> str
    lines = get_file_lines(dist, 'INSTALLER')
    if lines is None:
        return ''
    for line in lines:
        if line.strip():
            return line.strip()
    return ''
