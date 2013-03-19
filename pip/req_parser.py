
"""
Requirement file constants and parsing functions.
"""

import os
import re
import shlex
import optparse

from pip.log import logger
from pip.download import get_file_content
from pip.req import InstallRequirement
from pip.backwardcompat import urlparse


# The different types of lines understood by the parser
REQUIREMENT = 0x1
REQUIREMENT_FILE = 0x2
REQUIREMENT_EDITABLE = 0x3
FINDLINKS = 0x4
INDEXURL = 0x5
EXTRAINDEXURL = 0x6
NOINDEX = 0x7
UNKNOWN = 0xFF

# Options and flags that can be set on REQUIREMENT lines
requirement_args = ['--install-options', '--global-options']
requirement_flags = []


def parse_requirements(filename, finder=None, comes_from=None, options=None):
    '''Parse a requirements file and yield InstallRequirement instances.
    @param fn: path or url to requirements file.
    @param finder: pip.index.PackageFinder or None
    @param comes_from: used as a source for generated InstallRequirements
    @param options: dictionary of options'''
    fn, content = get_file_content(filename, comes_from=comes_from)
    for item in parse_content(filename, content, finder, comes_from, options):
        yield item


def parse_content(filename, content, finder=None, comes_from=None, options=None):
    content = ignore_comments(content.splitlines())
    content = join_lines(content)
    content = (line.strip() for line in content)

    for nr, line in enumerate(content):
        nr += 1

        linetype, value = parse_line(line, nr, filename)

        if linetype == REQUIREMENT:
            comes_from = '-r %s (line %s)' % (filename, nr)
            req, opts = value
            yield InstallRequirement.from_line(req, comes_from, options=opts)

        if linetype == REQUIREMENT_EDITABLE:
            comes_from = '-r %s (line %s)' % (filename, nr)
            default_vcs = options.default_vcs if options else None
            yield InstallRequirement.from_editable(value, comes_from, default_vcs)

        if linetype == REQUIREMENT_FILE:
            parser = parse_requirements(value, finder, filename, options)
            for item in parser:
                yield item

        if linetype == FINDLINKS and finder:
            finder.find_links.append(value)

        if linetype == INDEXURL and finder:
            finder.index_urls = [value]

        if linetype == EXTRAINDEXURL and finder:
            finder.index_urls.append(value)

        if linetype == NOINDEX:
            finder.index_urls = []

        if linetype == UNKNOWN:
            msg = 'Ignoring unrecognized line at %s:%d: %s'
            logger.info(msg, filename, nr, value)


def parse_line(line, number, filename, opts=True):
    if not line.startswith('-'):
        opts = get_options(line) if opts else {}

        # make sure that install|global_options are lists
        for i in ('install_options', 'global_options'):
            if i in opts:
                opts[i] = shlex.split(opts[i]) if opts[i] else []

        line = line.split('--')[0].strip()
        return REQUIREMENT, (line, opts)

    if line.startswith('-e') or line.startswith('--editable'):
        _, line = re.split(r'[\s=]', line, 1)
        return REQUIREMENT_EDITABLE, line.strip()

    if line.startswith('-r') or line.startswith('--requirement'):
        _, req_url = re.split(r'[\s=]', line, 1)
        if re.search(r'^(http|https|file):', filename, re.I):
            req_url = urlparse.urljoin(filename, req_url)  # relative to an url
        else:
            req_url = os.path.join(os.path.dirname(filename), req_url)
        return REQUIREMENT_FILE, req_url

    if line.startswith('-f') or line.startswith('--find-links'):
        _, line = re.split(r'[\s=]', line, 1)
        # FIXME: it would be nice to keep track of the source of
        # the find_links: support a find-links local path relative
        # to a requirements file
        reqs_file_dir = os.path.dirname(os.path.abspath(filename))
        relative_to_reqs_file = os.path.join(reqs_file_dir, line)
        if os.path.exists(relative_to_reqs_file):
            line = relative_to_reqs_file
        return FINDLINKS, line

    if line.startswith('-i') or line.startswith('--index-url'):
        _, line = re.split(r'[\s=]', line, 1)
        return INDEXURL, line

    if line.startswith('--extra-index-url'):
        _, line = re.split(r'[\s=]', line, 1)
        return EXTRAINDEXURL, line

    if line.startswith('--no-index'):
        return NOINDEX, None

    if line.startswith('-Z') or line.startswith('--always-unzip'):
        return UNKNOWN, line  # backwards compatibility

    return UNKNOWN, line


_option_parser_cache = {}
def get_options_parser(flags, args):
    if (flags, args) in _option_parser_cache:
        return _option_parser_cache[(flags, args)]

    parser = optparse.OptionParser()
    for flag in flags:
        parser.add_option(flag, action='store_true')
    for arg in args:
        parser.add_option(arg, action='store')

    _option_parser_cache[(flags, args)] = parser
    return parser


def get_options(line, flags=None, args=None):
    '''Parse options and flags from a requirement line. Example:
    >>> get_options('INITools --one --options="--two", ['--one'], ['--options'])
    {'--one' : True, '--options' : "--two"}'''
    args = args if args else requirement_args
    flags = flags if flags else requirement_flags

    parser = get_options_parser(tuple(flags), tuple(args))
    opts, args = parser.parse_args(shlex.split(line))
    return opts.__dict__


def join_lines(it):
    '''Joins a line that ends in a '\' with the previous line.'''
    # TODO: handle '\ '
    # TODO: handle '\' on last line
    lines = []
    for line in it:
        if not line.endswith('\\'):
            if lines:
                lines.append(line)
                yield ''.join(lines)
                lines = []
            else:
                yield line
        else:
            lines.append(line.strip('\\'))


def ignore_comments(it):
    'Filters empty or commented lines.'
    for line in it:
        if line and not line.startswith('#'):
            yield line
