from __future__ import absolute_import

import os
import re

from pip._vendor.six.moves.urllib import parse as urllib_parse

from pip.download import get_file_content
from pip.req.req_install import InstallRequirement
from pip.utils import normalize_name

_scheme_re = re.compile(r'^(http|https|file):', re.I)


def parse_requirements(filename, finder=None, comes_from=None, options=None,
                       session=None):
    if session is None:
        raise TypeError(
            "parse_requirements() missing 1 required keyword argument: "
            "'session'"
        )

    skip_match = None
    skip_regex = options.skip_requirements_regex if options else None
    if skip_regex:
        skip_match = re.compile(skip_regex)
    reqs_file_dir = os.path.dirname(os.path.abspath(filename))
    filename, content = get_file_content(
        filename,
        comes_from=comes_from,
        session=session,
    )
    for line_number, line in enumerate(content.splitlines(), 1):
        line = line.strip()

        # Remove comments from file
        line = re.sub(r"(^|\s)#.*$", "", line)

        if not line or line.startswith('#'):
            continue
        if skip_match and skip_match.search(line):
            continue
        if line.startswith('-r') or line.startswith('--requirement'):
            if line.startswith('-r'):
                req_url = line[2:].strip()
            else:
                req_url = line[len('--requirement'):].strip().strip('=')
            if _scheme_re.search(filename):
                # Relative to a URL
                req_url = urllib_parse.urljoin(filename, req_url)
            elif not _scheme_re.search(req_url):
                req_url = os.path.join(os.path.dirname(filename), req_url)
            for item in parse_requirements(
                    req_url, finder,
                    comes_from=filename,
                    options=options,
                    session=session):
                yield item
        elif line.startswith('-Z') or line.startswith('--always-unzip'):
            # No longer used, but previously these were used in
            # requirement files, so we'll ignore.
            pass
        elif line.startswith('-f') or line.startswith('--find-links'):
            if line.startswith('-f'):
                line = line[2:].strip()
            else:
                line = line[len('--find-links'):].strip().lstrip('=')
            # FIXME: it would be nice to keep track of the source of
            # the find_links:
            # support a find-links local path relative to a requirements file
            relative_to_reqs_file = os.path.join(reqs_file_dir, line)
            if os.path.exists(relative_to_reqs_file):
                line = relative_to_reqs_file
            if finder:
                finder.find_links.append(line)
        elif line.startswith('-i') or line.startswith('--index-url'):
            if line.startswith('-i'):
                line = line[2:].strip()
            else:
                line = line[len('--index-url'):].strip().lstrip('=')
            if finder:
                finder.index_urls = [line]
        elif line.startswith('--extra-index-url'):
            line = line[len('--extra-index-url'):].strip().lstrip('=')
            if finder:
                finder.index_urls.append(line)
        elif line.startswith('--use-wheel'):
            # Default in 1.5
            pass
        elif line.startswith('--no-use-wheel'):
            if finder:
                finder.use_wheel = False
        elif line.startswith('--no-index'):
            if finder:
                finder.index_urls = []
        elif line.startswith("--allow-external"):
            line = line[len("--allow-external"):].strip().lstrip("=")
            if finder:
                finder.allow_external |= set([normalize_name(line).lower()])
        elif line.startswith("--allow-all-external"):
            if finder:
                finder.allow_all_external = True
        # Remove in 7.0
        elif line.startswith("--no-allow-external"):
            pass
        # Remove in 7.0
        elif line.startswith("--no-allow-insecure"):
            pass
        # Remove after 7.0
        elif line.startswith("--allow-insecure"):
            line = line[len("--allow-insecure"):].strip().lstrip("=")
            if finder:
                finder.allow_unverified |= set([normalize_name(line).lower()])
        elif line.startswith("--allow-unverified"):
            line = line[len("--allow-unverified"):].strip().lstrip("=")
            if finder:
                finder.allow_unverified |= set([normalize_name(line).lower()])
        else:
            comes_from = '-r %s (line %s)' % (filename, line_number)
            if line.startswith('-e') or line.startswith('--editable'):
                if line.startswith('-e'):
                    line = line[2:].strip()
                else:
                    line = line[len('--editable'):].strip().lstrip('=')
                req = InstallRequirement.from_editable(
                    line,
                    comes_from=comes_from,
                    default_vcs=options.default_vcs if options else None,
                    isolated=options.isolated_mode if options else False,
                )
            else:
                req = InstallRequirement.from_line(
                    line,
                    comes_from,
                    isolated=options.isolated_mode if options else False,
                )
            yield req
