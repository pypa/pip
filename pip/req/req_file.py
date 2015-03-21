
"""
Routines for parsing requirements files (i.e. requirements.txt).
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
from pip.exceptions import RequirementsFileParseError
from pip.utils import normalize_name
from pip import cmdoptions


# ----------------------------------------------------------------------------
# Flags that don't take any options.
parser_flags = set([
    '--no-index',
    '--allow-all-external',
    '--no-use-wheel',
])

# Flags that take options.
parser_options = set([
    '-i', '--index-url',
    '-f', '--find-links',
    '--extra-index-url',
    '--allow-external',
    '--allow-unverified',
])

# Encountering any of these is a no-op.
parser_compat = set([
    '-Z', '--always-unzip',
    '--use-wheel',          # Default in 1.5
    '--no-allow-external',  # Remove in 7.0
    '--no-allow-insecure',  # Remove in 7.0
])

# ----------------------------------------------------------------------------
# Requirement lines may take options. For example:
#   INITools==0.2 --install-option="--prefix=/opt" --global-option="-v"
# We use optparse to reliably parse these lines.
_req_parser = optparse.OptionParser(add_help_option=False)
_req_parser.add_option(cmdoptions.install_options.make())
_req_parser.add_option(cmdoptions.global_options.make())
_req_parser.disable_interspersed_args()


# By default optparse sys.exits on parsing errors. We want to wrap
# that in our own exception.
def parser_exit(self, msg):
    raise RequirementsFileParseError(msg)
_req_parser.exit = parser_exit

# ----------------------------------------------------------------------------
# Pre-compiled regex.
_scheme_re = re.compile(r'^(http|https|file):', re.I)
_comment_re = re.compile(r'(^|\s)+#.*$')

# ----------------------------------------------------------------------------
# The types of lines understood by the requirements file parser.
REQUIREMENT = 0
REQUIREMENT_FILE = 1
REQUIREMENT_EDITABLE = 2
FLAG = 3
OPTION = 4
IGNORE = 5


def parse_requirements(filename, finder=None, comes_from=None, options=None,
                       session=None):
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

    parser = parse_content(
        filename, content, finder, comes_from, options, session
    )

    for item in parser:
        yield item


def parse_content(filename, content, finder=None, comes_from=None,
                  options=None, session=None):

    # Split, sanitize and join lines with continuations.
    content = content.splitlines()
    content = ignore_comments(content)
    content = join_lines(content)

    # Optionally exclude lines that match '--skip-requirements-regex'.
    skip_regex = options.skip_requirements_regex if options else None
    if skip_regex:
        content = filterfalse(re.compile(skip_regex).search, content)

    for line_number, line in enumerate(content, 1):
        # The returned value depends on the type of line that was parsed.
        linetype, value = parse_line(line)

        # ---------------------------------------------------------------------
        if linetype == REQUIREMENT:
            req, opts = value
            comes_from = '-r %s (line %s)' % (filename, line_number)
            isolated = options.isolated_mode if options else False
            yield InstallRequirement.from_line(
                req, comes_from, isolated=isolated, options=opts
            )

        # ---------------------------------------------------------------------
        elif linetype == REQUIREMENT_EDITABLE:
            comes_from = '-r %s (line %s)' % (filename, line_number)
            isolated = options.isolated_mode if options else False
            default_vcs = options.default_vcs if options else None
            yield InstallRequirement.from_editable(
                value, comes_from=comes_from,
                default_vcs=default_vcs, isolated=isolated
            )

        # ---------------------------------------------------------------------
        elif linetype == REQUIREMENT_FILE:
            if _scheme_re.search(filename):
                # Relative to an URL.
                req_url = urllib_parse.urljoin(filename, value)
            elif not _scheme_re.search(value):
                req_dir = os.path.dirname(filename)
                req_url = os.path.join(os.path.dirname(filename), value)
            # TODO: Why not use `comes_from='-r {} (line {})'` here as well?
            parser = parse_requirements(
                req_url, finder, comes_from, options, session
            )
            for req in parser:
                yield req

        # ---------------------------------------------------------------------
        elif linetype == FLAG:
            if not finder:
                continue

            if finder and value == '--no-use-wheel':
                finder.use_wheel = False
            elif value == '--no-index':
                finder.index_urls = []
            elif value == '--allow-all-external':
                finder.allow_all_external = True

        # ---------------------------------------------------------------------
        elif linetype == OPTION:
            if not finder:
                continue

            opt, value = value
            if opt == '-i' or opt == '--index-url':
                finder.index_urls = [value]
            elif opt == '--extra-index-url':
                finder.index_urls.append(value)
            elif opt == '--allow-external':
                finder.allow_external |= set([normalize_name(value).lower()])
            elif opt == '--allow-insecure':
                # Remove after 7.0
                finder.allow_unverified |= set([normalize_name(line).lower()])
            elif opt == '-f' or opt == '--find-links':
                # FIXME: it would be nice to keep track of the source
                # of the find_links: support a find-links local path
                # relative to a requirements file.
                req_dir = os.path.dirname(os.path.abspath(filename))
                relative_to_reqs_file = os.path.join(req_dir, value)
                if os.path.exists(relative_to_reqs_file):
                    value = relative_to_reqs_file
                finder.find_links.append(value)

        # ---------------------------------------------------------------------
        elif linetype == IGNORE:
            pass


def parse_line(line):
    if not line.startswith('-'):
        # Split the requirement from the options.
        if ' --' in line:
            req, opts = line.split(' --', 1)
            opts = parse_requirement_options('--%s' % opts)
        else:
            req = line
            opts = {}

        return REQUIREMENT, (req, opts)

    firstword, rest = partition_line(line)
    # -------------------------------------------------------------------------
    if firstword == '-e' or firstword == '--editable':
        return REQUIREMENT_EDITABLE, rest

    # -------------------------------------------------------------------------
    if firstword == '-r' or firstword == '--requirement':
        return REQUIREMENT_FILE, rest

    # -------------------------------------------------------------------------
    if firstword in parser_flags:
        if rest:
            msg = 'Option %r does not accept values.' % firstword
            raise RequirementsFileParseError(msg)
        return FLAG, firstword

    # -------------------------------------------------------------------------
    if firstword in parser_options:
        if not rest:
            msg = 'Option %r requires value.' % firstword
            raise RequirementsFileParseError(msg)
        return OPTION, (firstword, rest)

    # -------------------------------------------------------------------------
    if firstword in parser_compat:
        return IGNORE, line


def parse_requirement_options(args):
    args = shlex.split(args)
    opts, _ = _req_parser.parse_args(args)

    if opts.install_options:
        opts.install_options = flat_shlex_split(opts.install_options)
    if opts.global_options:
        opts.global_options = flat_shlex_split(opts.global_options)

    # Remove None keys from result.
    keys = [opt for opt in opts.__dict__ if getattr(opts, opt) is None]
    for key in keys:
        delattr(opts, key)

    return opts.__dict__


# -----------------------------------------------------------------------------
# Utility functions related to requirements file parsing.
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
        line = _comment_re.sub('', line)
        line = line.strip()
        if line:
            yield line


def partition_line(line):
    firstword, _, rest = line.partition('=')
    firstword = firstword.strip()

    if ' ' in firstword:
        firstword, _, rest = line.partition(' ')
        firstword = firstword.strip()

    rest = rest.strip()
    return firstword, rest


def flat_shlex_split(x):
    '''
    >>> flat_shlex_split(['--one --two', '--three "4" --five'])
    ['--one', '--two', '--three', '4', '--five']
    '''
    return [j for i in x for j in shlex.split(i)]


__all__ = 'parse_requirements'
