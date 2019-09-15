import os.path
from contextlib import contextmanager

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement

from pip._internal.models.link import Link
from pip._internal.req.constructors import _strip_extras
from pip._internal.utils.misc import path_to_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, Set, Tuple


__all__ = [
    'RequirementInfo',
    'RequirementParsingError',
    'parse_requirement_text',
]


PATH_MARKER_SEP = ';'
URL_MARKER_SEP = '; '


def convert_extras(extras):
    # type: (Optional[str]) -> Set[str]
    if extras:
        return Requirement("placeholder" + extras.lower()).extras
    else:
        return set()


def strip_and_convert_extras(text):
    # type: (str) -> Tuple[str, Set[str]]
    result, extras = _strip_extras(text)
    return result, convert_extras(extras)


class RequirementParsingError(Exception):
    def __init__(self, type_tried, cause):
        # type: (str, Exception) -> None
        self.type_tried = type_tried
        self.cause = cause


class RequirementInfo(object):
    def __init__(
        self,
        requirement,  # type: Optional[Requirement]
        link,         # type: Optional[Link]
        markers,      # type: Optional[Marker]
        extras,       # type: Set[str]
    ):
        self.requirement = requirement
        self.link = link
        self.markers = markers
        self.extras = extras

    @property
    def is_unnamed(self):
        return self.requirement is None

    @property
    def is_name_based(self):
        return self.link is None

    def __repr__(self):
        return '<RequirementInfo({!r}, {!r}, {!r}, {!r})>'.format(
            self.requirement, self.link, self.markers, self.extras,
        )


def requirement_info_from_requirement(text):
    # type: (str) -> RequirementInfo
    req = Requirement(text)
    return RequirementInfo(
        req,
        Link(req.url) if req.url else None,
        req.marker,
        req.extras,
    )


def requirement_info_from_url(url):
    # type: (str) -> RequirementInfo
    try:
        url, marker_text = url.split(URL_MARKER_SEP)
    except ValueError:
        marker = None
    else:
        marker = Marker(marker_text)

    # Prevent stripping extras out of URL fragment
    if '#egg=' not in url:
        url, extras = strip_and_convert_extras(url)
    else:
        extras = set()

    link = Link(url)

    egg_fragment = link.egg_fragment

    req = None  # type: Optional[Requirement]
    if egg_fragment:
        req = Requirement(egg_fragment)
        # We prefer fragment extras if present.
        if req.extras:
            extras = req.extras

    return RequirementInfo(req, link, marker, extras)


def requirement_info_from_path(path):
    # type: (str) -> RequirementInfo
    try:
        path, markers = path.split(PATH_MARKER_SEP)
    except ValueError:
        markers = ''
    else:
        markers = URL_MARKER_SEP + markers

    path, extras = _strip_extras(path)
    if extras is None:
        extras = ''

    url = path_to_url(path)

    return requirement_info_from_url(
        '{}{}{}'.format(url, extras, markers),
    )


def looks_like_direct_reference(text):
    try:
        assert text.index('@') < text.index('://')
    except (AssertionError, ValueError):
        return False
    else:
        return True


def looks_like_url(text):
    # type: (str) -> bool
    return '://' in text


def looks_like_path(text):
    # type: (str) -> bool
    return (
        os.path.sep in text or
        os.path.altsep is not None and os.path.altsep in text or
        text.startswith('.')
    )


@contextmanager
def try_parse_as(message):
    try:
        yield
    except Exception as e:
        raise RequirementParsingError(message, e)


def parse_requirement_text(text):
    # type: (str) -> RequirementInfo
    # Only search before any ';', since marker strings can
    # contain most kinds of text.
    search_text = text.split(';', 1)[0]

    if looks_like_direct_reference(search_text):
        with try_parse_as('direct reference'):
            return requirement_info_from_requirement(text)

    if looks_like_url(search_text):
        with try_parse_as('url'):
            return requirement_info_from_url(text)

    if looks_like_path(search_text):
        with try_parse_as('path'):
            return requirement_info_from_path(text)

    with try_parse_as('name-based reference'):
        return requirement_info_from_requirement(text)
