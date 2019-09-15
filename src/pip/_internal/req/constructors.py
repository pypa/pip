"""Backing implementation for InstallRequirement's various constructors

The idea here is that these formed a major chunk of InstallRequirement's size
so, moving them and support code dedicated to them outside of that class
helps creates for better understandability for the rest of the code.

These are meant to be used elsewhere within pip to create instances of
InstallRequirement.
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import logging
import os

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
from pip._vendor.packaging.specifiers import Specifier
from pip._vendor.pkg_resources import RequirementParseError, parse_requirements

from pip._internal.exceptions import InstallationError
from pip._internal.models.index import PyPI, TestPyPI
from pip._internal.models.link import Link
from pip._internal.pyproject import make_pyproject_path
from pip._internal.req.parsing import (
    RequirementParsingError,
    _strip_extras,
    parse_requirement_text,
)
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.misc import (
    ARCHIVE_EXTENSIONS,
    is_installable_dir,
    path_to_url,
    splitext,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.urls import url_to_path
from pip._internal.vcs import is_url, vcs
from pip._internal.wheel import Wheel

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Dict, Optional, Set, Tuple, Union,
    )
    from pip._internal.cache import WheelCache


__all__ = [
    "install_req_from_editable", "install_req_from_line",
    "parse_editable"
]

logger = logging.getLogger(__name__)
operators = Specifier._operators.keys()


def is_archive_file(name):
    # type: (str) -> bool
    """Return True if `name` is a considered as an archive file."""
    ext = splitext(name)[1].lower()
    if ext in ARCHIVE_EXTENSIONS:
        return True
    return False


def parse_editable(editable_req):
    # type: (str) -> Tuple[Optional[str], str, Optional[Set[str]]]
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """

    url = editable_req

    # If a file path is specified with extras, strip off the extras.
    url_no_extras, extras = _strip_extras(url)

    if os.path.isdir(url_no_extras):
        if not os.path.exists(os.path.join(url_no_extras, 'setup.py')):
            msg = (
                'File "setup.py" not found. Directory cannot be installed '
                'in editable mode: {}'.format(os.path.abspath(url_no_extras))
            )
            pyproject_path = make_pyproject_path(url_no_extras)
            if os.path.isfile(pyproject_path):
                msg += (
                    '\n(A "pyproject.toml" file was found, but editable '
                    'mode currently requires a setup.py based build.)'
                )
            raise InstallationError(msg)

        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith('file:'):
        package_name = Link(url_no_extras).egg_fragment
        if extras:
            return (
                package_name,
                url_no_extras,
                Requirement("placeholder" + extras.lower()).extras,
            )
        else:
            return package_name, url_no_extras, None

    for version_control in vcs:
        if url.lower().startswith('%s:' % version_control):
            url = '%s+%s' % (version_control, url)
            break

    if '+' not in url:
        raise InstallationError(
            '{} is not a valid editable requirement. '
            'It should either be a path to a local project or a VCS URL '
            '(beginning with svn+, git+, hg+, or bzr+).'.format(editable_req)
        )

    vc_type = url.split('+', 1)[0].lower()

    if not vcs.get_backend(vc_type):
        error_message = 'For --editable=%s only ' % editable_req + \
            ', '.join([backend.name + '+URL' for backend in vcs.backends]) + \
            ' is currently supported'
        raise InstallationError(error_message)

    package_name = Link(url).egg_fragment
    if not package_name:
        raise InstallationError(
            "Could not detect requirement name for '%s', please specify one "
            "with #egg=your_package_name" % editable_req
        )
    return package_name, url, None


def deduce_helpful_msg(req):
    # type: (str) -> str
    """Returns helpful msg in case requirements file does not exist,
    or cannot be parsed.

    :params req: Requirements file path
    """
    msg = ""
    # Try to parse and check if it is a requirements file.
    try:
        with open(req, 'r') as fp:
            # parse first line only
            next(parse_requirements(fp.read()))
            msg += " The argument you provided " + \
                "(%s) appears to be a" % (req) + \
                " requirements file. If that is the" + \
                " case, use the '-r' flag to install" + \
                " the packages specified within it."
    except RequirementParseError:
        logger.debug("Cannot parse '%s' as requirements \
        file" % (req), exc_info=True)
    return msg


# ---- The actual constructors follow ----


def install_req_from_editable(
    editable_req,  # type: str
    comes_from=None,  # type: Optional[str]
    use_pep517=None,  # type: Optional[bool]
    isolated=False,  # type: bool
    options=None,  # type: Optional[Dict[str, Any]]
    wheel_cache=None,  # type: Optional[WheelCache]
    constraint=False  # type: bool
):
    # type: (...) -> InstallRequirement
    name, url, extras_override = parse_editable(editable_req)
    if url.startswith('file:'):
        source_dir = url_to_path(url)
    else:
        source_dir = None

    if name is not None:
        try:
            req = Requirement(name)
        except InvalidRequirement:
            raise InstallationError("Invalid requirement: '%s'" % name)
    else:
        req = None
    return InstallRequirement(
        req, comes_from, source_dir=source_dir,
        editable=True,
        link=Link(url),
        constraint=constraint,
        use_pep517=use_pep517,
        isolated=isolated,
        options=options if options else {},
        wheel_cache=wheel_cache,
        extras=extras_override or (),
    )


def install_req_from_line(
    name,  # type: str
    comes_from=None,  # type: Optional[Union[str, InstallRequirement]]
    use_pep517=None,  # type: Optional[bool]
    isolated=False,  # type: bool
    options=None,  # type: Optional[Dict[str, Any]]
    wheel_cache=None,  # type: Optional[WheelCache]
    constraint=False,  # type: bool
    line_source=None,  # type: Optional[str]
):
    # type: (...) -> InstallRequirement
    """Creates an InstallRequirement from a name, which might be a
    requirement, directory containing 'setup.py', filename, or URL.

    :param line_source: An optional string describing where the line is from,
        for logging purposes in case of an error.
    """
    def with_source(text):
        if not line_source:
            return text
        return '{} (from {})'.format(text, line_source)

    try:
        req = parse_requirement_text(name)
    except RequirementParsingError as e:
        if e.type_tried not in ['path', 'url'] and (
            '=' in name and not any(op in name for op in operators)
        ):
            add_msg = "= is not a valid operator. Did you mean == ?"
        else:
            add_msg = "(tried parsing as {})".format(e.type_tried)

        msg = with_source('Invalid requirement: {!r}'.format(name))
        msg += '\nHint: {}'.format(add_msg)
        raise InstallationError(msg)
    if is_url(name):
        marker_sep = '; '
    else:
        marker_sep = ';'
    if marker_sep in name:
        name, markers_as_string = name.split(marker_sep, 1)
        markers_as_string = markers_as_string.strip()
        if not markers_as_string:
            markers = None
        else:
            markers = Marker(markers_as_string)
    else:
        markers = None
    name = name.strip()
    req_as_string = None
    link = req.link
    extras_as_string = None

    if link and link.scheme == 'file':
        p = link.path
        if not os.path.exists(p):
            raise InstallationError(
                with_source(
                    "Requirement '{}' looks like a path, but the "
                    'file/directory does not exist'.format(name)
                )
            )

        if os.path.isdir(p):
            if not is_installable_dir(p):
                raise InstallationError(
                    "Directory %r is not installable. Neither 'setup.py' "
                    "nor 'pyproject.toml' found." % name
                )
        elif not is_archive_file(p) and not link.is_wheel:
            raise InstallationError(
                "Invalid requirement: {!r}, files must be wheels or "
                'archives'.format(name) + deduce_helpful_msg(p)
            )

    if extras_as_string:
        extras = Requirement("placeholder" + extras_as_string.lower()).extras
    else:
        extras = ()
    # wheel file
    if link and link.is_wheel:
        wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
        wheel_req = "%s==%s" % (wheel.name, wheel.version)
        try:
            req.requirement = Requirement(wheel_req)
        except InvalidRequirement:
            pass

    return InstallRequirement(
        req.requirement, comes_from, link=link, markers=markers,
        use_pep517=use_pep517, isolated=isolated,
        options=options if options else {},
        wheel_cache=wheel_cache,
        constraint=constraint,
        extras=extras,
    )


def install_req_from_req_string(
    req_string,  # type: str
    comes_from=None,  # type: Optional[InstallRequirement]
    isolated=False,  # type: bool
    wheel_cache=None,  # type: Optional[WheelCache]
    use_pep517=None  # type: Optional[bool]
):
    # type: (...) -> InstallRequirement
    try:
        req = Requirement(req_string)
    except InvalidRequirement:
        raise InstallationError("Invalid requirement: '%s'" % req_string)

    domains_not_allowed = [
        PyPI.file_storage_domain,
        TestPyPI.file_storage_domain,
    ]
    if (req.url and comes_from and comes_from.link and
            comes_from.link.netloc in domains_not_allowed):
        # Explicitly disallow pypi packages that depend on external urls
        raise InstallationError(
            "Packages installed from PyPI cannot depend on packages "
            "which are not also hosted on PyPI.\n"
            "%s depends on %s " % (comes_from.name, req)
        )

    return InstallRequirement(
        req, comes_from, isolated=isolated, wheel_cache=wheel_cache,
        use_pep517=use_pep517
    )
