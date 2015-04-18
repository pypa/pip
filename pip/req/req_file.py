"""
Requirements file parsing
"""

from __future__ import absolute_import

import os
import re
import shlex
import optparse

from pip._vendor.six.moves.urllib import parse as urllib_parse
from pip._vendor.six.moves import filterfalse

from pip.download import get_file_content
from pip.req.req_install import InstallRequirement
from pip.exceptions import (RequirementsFileParseError,
                            ReqFileOnlyOneReqPerLineError,
                            ReqFileOnleOneOptionPerLineError,
                            ReqFileOptionNotAllowedWithReqError)
from pip.utils import normalize_name
from pip import cmdoptions

__all__ = ['parse_requirements']

SCHEME_RE = re.compile(r'^(http|https|file):', re.I)
COMMENT_RE = re.compile(r'(^|\s)+#.*$')

SUPPORTED_OPTIONS = [
    cmdoptions.editable,
    cmdoptions.requirements,
    cmdoptions.no_index,
    cmdoptions.index_url,
    cmdoptions.find_links,
    cmdoptions.extra_index_url,
    cmdoptions.allow_external,
    cmdoptions.no_allow_external,
    cmdoptions.allow_unsafe,
    cmdoptions.no_allow_unsafe,
    cmdoptions.use_wheel,
    cmdoptions.no_use_wheel,
    cmdoptions.always_unzip,
]

# options allowed on requirement lines
SUPPORTED_OPTIONS_REQ = [
    cmdoptions.install_options,
    cmdoptions.global_options,
]


def parse_requirements(filename, finder=None, comes_from=None, options=None,
                       session=None, cache_root=None):
    """
    Parse a requirements file and yield InstallRequirement instances.

    :param filename:   Path or url of requirements file.
    :param finder:     Instance of pip.index.PackageFinder.
    :param comes_from: Origin description of requirements.
    :param options:    Global options.
    :param session:    Instance of pip.download.PipSession.
    """
    if session is None:
        raise TypeError(
            "parse_requirements() missing 1 required keyword argument: "
            "'session'"
        )

    _, content = get_file_content(
        filename, comes_from=comes_from, session=session
    )

    lines = content.splitlines()
    lines = ignore_comments(lines)
    lines = join_lines(lines)
    lines = skip_regex(lines, options)

    for line_number, line in enumerate(lines, 1):
        req_iter = process_line(line, filename, line_number, finder,
                                comes_from, options, session)
        for req in req_iter:
            yield req


def process_line(line, filename, line_number, finder=None, comes_from=None,
                 options=None, session=None, cache_root=None):
    """
    Process a single requirements line; This can result in creating/yielding
    requirements, or updating the finder.
    """

    parser = build_parser()
    args = shlex.split(line)
    opts, args = parser.parse_args(args)
    req = None

    if args:
        # don't allow multiple requirements
        if len(args) > 1:
            msg = 'Only one requirement supported per line.'
            raise ReqFileOnlyOneReqPerLineError(msg)
        for key, value in opts.__dict__.items():
            # only certain options can be on req lines
            dest_strings = [o().dest for o in SUPPORTED_OPTIONS_REQ]
            if value is not None and key not in dest_strings:
                # get the option string
                # the option must be supported to get to this point
                for o in SUPPORTED_OPTIONS:
                    o = o()
                    if o.dest == key:
                        opt_string = o.get_opt_string()
                msg = ('Option not supported on a'
                       ' requirement line: %s' % opt_string)
                raise ReqFileOptionNotAllowedWithReqError(msg)
        req = args[0]

    # don't allow multiple/different options (on non-req lines)
    if not args and len(
            [v for v in opts.__dict__.values() if v is not None]) > 1:
        msg = 'Only one option allowed per line.'
        raise ReqFileOnleOneOptionPerLineError(msg)

    # yield a line requirement
    if req:
        comes_from = '-r %s (line %s)' % (filename, line_number)
        isolated = options.isolated_mode if options else False
        # trim the None items
        keys = [opt for opt in opts.__dict__ if getattr(opts, opt) is None]
        for key in keys:
            delattr(opts, key)
        yield InstallRequirement.from_line(
            req, comes_from, isolated=isolated, options=opts.__dict__
        )

    # yield an editable requirement
    elif opts.editables:
        comes_from = '-r %s (line %s)' % (filename, line_number)
        isolated = options.isolated_mode if options else False
        default_vcs = options.default_vcs if options else None
        yield InstallRequirement.from_editable(
            opts.editables[0], comes_from=comes_from,
            default_vcs=default_vcs, isolated=isolated
        )

    # parse a nested requirements file
    elif opts.requirements:
        req_file = opts.requirements[0]
        if SCHEME_RE.search(filename):
            # Relative to an URL.
            req_url = urllib_parse.urljoin(filename, req_file)
        elif not SCHEME_RE.search(req_file):
            req_dir = os.path.dirname(filename)
            req_url = os.path.join(os.path.dirname(filename), req_file)
        # TODO: Why not use `comes_from='-r {} (line {})'` here as well?
        parser = parse_requirements(
            req_url, finder, comes_from, options, session, cache_root
        )
        for req in parser:
            yield req

    # set finder options
    elif finder:
        if opts.use_wheel is not None:
            finder.use_wheel = opts.use_wheel
        elif opts.no_index is not None:
            finder.index_urls = []
        elif opts.allow_all_external is not None:
            finder.allow_all_external = opts.allow_all_external
        elif opts.index_url is not None:
            finder.index_urls = [opts.index_url]
        elif opts.extra_index_urls is not None:
            finder.index_urls.extend(opts.extra_index_urls)
        elif opts.allow_external is not None:
            finder.allow_external |= set(
                [normalize_name(v).lower() for v in opts.allow_external])
        elif opts.allow_unverified is not None:
            # Remove after 7.0
            finder.allow_unverified |= set(
                [normalize_name(v).lower() for v in opts.allow_unverified])
        elif opts.find_links is not None:
            # FIXME: it would be nice to keep track of the source
            # of the find_links: support a find-links local path
            # relative to a requirements file.
            value = opts.find_links[0]
            req_dir = os.path.dirname(os.path.abspath(filename))
            relative_to_reqs_file = os.path.join(req_dir, value)
            if os.path.exists(relative_to_reqs_file):
                value = relative_to_reqs_file
            finder.find_links.append(value)


def build_parser():
    """
    Return a parser for parsing requirement lines
    """
    parser = optparse.OptionParser(add_help_option=False)

    options = SUPPORTED_OPTIONS + SUPPORTED_OPTIONS_REQ
    for option in options:
        option = option()
        # we want no default values; defaults are handled in `pip install`
        # parsing. just concerned with values that are specifically set.
        option.default = None
        parser.add_option(option)

    # By default optparse sys.exits on parsing errors. We want to wrap
    # that in our own exception.
    def parser_exit(self, msg):
        raise RequirementsFileParseError(msg)
    parser.exit = parser_exit

    return parser


def join_lines(iterator):
    """
    Joins a line ending in '\' with the previous line.
    """
    lines = []
    for line in iterator:
        if not line.endswith('\\'):
            if lines:
                lines.append(line)
                yield ''.join(lines)
                lines = []
            else:
                yield line
        else:
            lines.append(line.strip('\\'))

    # TODO: handle space after '\'.
    # TODO: handle '\' on last line.


def ignore_comments(iterator):
    """
    Strips and filters empty or commented lines.
    """
    for line in iterator:
        line = COMMENT_RE.sub('', line)
        line = line.strip()
        if line:
            yield line


def skip_regex(lines, options):
    """
    Optionally exclude lines that match '--skip-requirements-regex'
    """
    skip_regex = options.skip_requirements_regex if options else None
    if skip_regex:
        lines = filterfalse(re.compile(skip_regex).search, lines)
    return lines
