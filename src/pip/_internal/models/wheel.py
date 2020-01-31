"""Represents a wheel file and provides access to the various parts of the
name that have meaning.
"""
import re
from collections import OrderedDict

from pip._vendor.packaging.tags import Tag

from pip._internal.exceptions import InvalidWheelFilename
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List


class Wheel(object):
    """A wheel file"""

    wheel_file_re = re.compile(
        r"""^(?P<namever>(?P<name>.+?)-(?P<ver>.*?))
        ((-(?P<build>\d[^-]*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
        \.whl|\.dist-info)$""",
        re.VERBOSE
    )

    def __init__(self, filename):
        # type: (str) -> None
        """
        :raises InvalidWheelFilename: when the filename is invalid for a wheel
        """
        wheel_info = self.wheel_file_re.match(filename)
        if not wheel_info:
            raise InvalidWheelFilename(
                "%s is not a valid wheel filename." % filename
            )
        self.filename = filename
        self.name = wheel_info.group('name').replace('_', '-')
        # we'll assume "_" means "-" due to wheel naming scheme
        # (https://github.com/pypa/pip/issues/1150)
        self.version = wheel_info.group('ver').replace('_', '-')
        self.build_tag = wheel_info.group('build')
        self.pyversions = wheel_info.group('pyver').split('.')
        self.abis = wheel_info.group('abi').split('.')
        self.plats = wheel_info.group('plat').split('.')

        # Adjust for any legacy custom PyPy tags found in pyversions
        missing_tags = _infer_missing_pypy_version_tags(self.pyversions)
        if missing_tags:
            self.pyversions.extend(missing_tags)

            deprecated(
                reason=(
                    "{} includes legacy PyPy version tags without the "
                    "corresponding standard tags ({})."
                ).format(self.filename, missing_tags),
                replacement=(
                    "for maintainers: use v0.34.0 or later of the wheel "
                    "project to create a correctly tagged {0} PyPy wheel. "
                    "For users: contact the maintainers of {0} to let "
                    "them know to regenerate their PyPy wheel(s)".format(
                        self.name
                    )
                ),
                gone_in="21.0",
                issue=7629,
            )

        # All the tag combinations from this file
        self.file_tags = {
            Tag(x, y, z) for x in self.pyversions
            for y in self.abis for z in self.plats
        }

    def get_formatted_file_tags(self):
        # type: () -> List[str]
        """Return the wheel's tags as a sorted list of strings."""
        return sorted(str(tag) for tag in self.file_tags)

    def support_index_min(self, tags):
        # type: (List[Tag]) -> int
        """Return the lowest index that one of the wheel's file_tag combinations
        achieves in the given list of supported tags.

        For example, if there are 8 supported tags and one of the file tags
        is first in the list, then return 0.

        :param tags: the PEP 425 tags to check the wheel against, in order
            with most preferred first.

        :raises ValueError: If none of the wheel's file tags match one of
            the supported tags.
        """
        return min(tags.index(tag) for tag in self.file_tags if tag in tags)

    def supported(self, tags):
        # type: (List[Tag]) -> bool
        """Return whether the wheel is compatible with one of the given tags.

        :param tags: the PEP 425 tags to check the wheel against.
        """
        return not self.file_tags.isdisjoint(tags)


def _is_legacy_pypy_tag(pyversion_tag):
    # type: (str) -> bool
    """Returns True if the given tag looks like a legacy custom PyPy tag

    :param pyversion_tag: pyversion tags to be checked
    """
    return (
        len(pyversion_tag) == 5 and
        pyversion_tag.startswith('pp') and
        pyversion_tag[2:].isdigit()
    )


# Note: the listed thresholds are the first non-alpha PyPy version that
#       *doesn't* report the given Python version in sys.version_info. This
#       means that PyPy 7.0.0 is handled as a Python 3.5 compatible release.
_PYPY3_COMPATIBILITY_TAG_THRESHOLDS = OrderedDict((
    ('pp32', (5, 2)),
    ('pp33', (5, 7)),
    ('pp35', (7, 1)),
    ('pp36', (8, 0))
    # The legacy custom PyPy wheel tags are not supported on PyPy 8.0.0+
))


def _infer_missing_pypy_version_tags(pyversions):
    # type: (List[str]) -> List[str]
    """Infer standard PyPy tags for any legacy PyPy tags, avoiding duplicates

    Returns an ordered list of the missing tags (which may be empty)

    :param pyversions: the list of pyversion tags to be checked
    """
    # Several wheel versions prior to 0.34.0 produced non-standard tags
    # for PyPy wheel archives. For backwards compatibility, we translate
    # those legacy custom tags to standard tags for PyPy versions prior to
    # PyPy 8.0.0.
    legacy_pypy_tags = [tag for tag in pyversions if _is_legacy_pypy_tag(tag)]
    if not legacy_pypy_tags:
        return []  # Nothing to do

    standard_tags = set()
    py3_tag_thresholds = _PYPY3_COMPATIBILITY_TAG_THRESHOLDS.items()
    for tag in legacy_pypy_tags:
        py_major, pypy_major, pypy_minor = map(int, tag[2:])
        if py_major == 2:
            standard_tags.add('pp27')
            continue
        if py_major > 3:
            continue
        pypy_version = (pypy_major, pypy_minor)
        for standard_tag, version_limit in py3_tag_thresholds:
            if pypy_version < version_limit:
                standard_tags.add(standard_tag)
                break

    if not standard_tags:
        return []  # Nothing to do

    existing_tags = set(pyversions)
    missing_tags = standard_tags - existing_tags
    if not missing_tags:
        return []  # Nothing to do

    # Order the tags to get consistent warning output
    return sorted(missing_tags)
