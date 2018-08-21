"""Backing implementation for InstallRequirement's various constructors

The idea here is that these formed a major chunk of InstallRequirement's size
so, moving them and support code dedicated to them outside of that class
helps creates for better understandability for the rest of the code.

These are meant to be used elsewhere within pip to create instances of
InstallRequirement.
"""

import os

from pip._vendor.packaging.requirements import InvalidRequirement, Requirement

# XXX: Temporarily importing _strip_extras
from pip._internal.download import path_to_url, url_to_path
from pip._internal.exceptions import InstallationError
from pip._internal.models.link import Link
from pip._internal.req.req_install import InstallRequirement, _strip_extras
from pip._internal.vcs import vcs

__all__ = ["install_req_from_editable", "parse_editable"]


def parse_editable(editable_req):
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
            raise InstallationError(
                "Directory %r is not installable. File 'setup.py' not found." %
                url_no_extras
            )
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
            '%s should either be a path to a local project or a VCS url '
            'beginning with svn+, git+, hg+, or bzr+' %
            editable_req
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


def install_req_from_editable(
    editable_req, comes_from=None, isolated=False, options=None,
    wheel_cache=None, constraint=False
):
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
        isolated=isolated,
        options=options if options else {},
        wheel_cache=wheel_cache,
        extras=extras_override or (),
    )
