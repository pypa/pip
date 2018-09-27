#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from pip._vendor import html5lib, six

# Copied from distlib.compat (to match pip's implementation).
if sys.version_info < (3, 4):
    unescape = six.moves.html_parser.HTMLParser().unescape
else:
    from html import unescape

EGG_INFO_RE = re.compile(r"([a-z0-9_.]+)-([a-z0-9_.!+-]+)", re.IGNORECASE)


def match_egg_info_version(egg_info, package_name, _egg_info_re=EGG_INFO_RE):
    """Pull the version part out of a string.

    :param egg_info: The string to parse. E.g. foo-2.1
    :param package_name: The name of the package this belongs to. None to
        infer the name. Note that this cannot unambiguously parse strings
        like foo-2-2 which might be foo, 2-2 or foo-2, 2.
    """
    match = _egg_info_re.search(egg_info)
    if not match:
        raise ValueError(egg_info)
    if package_name is None:
        return match.group(0).split("-", 1)[-1]
    name = match.group(0).lower()
    # To match the "safe" name that pkg_resources creates:
    name = name.replace('_', '-')
    # project name and version must be separated by a dash
    look_for = package_name.lower() + "-"
    if name.startswith(look_for):
        return match.group(0)[len(look_for):]
    return None


def _parse_base_url(document, page_url):
    """Get the base URL of this document.

    This looks for a ``<base>`` tag in the HTML document. If present, its href
    attribute denotes the base URL of anchor tags in the document. If there is
    no such tag (or if it does not have a valid href attribute), the HTML
    file's URL is used as the base URL.

    :param document: An HTML document representation. The current
        implementation expects the result of ``html5lib.parse()``.
    :param page_url: The URL of the HTML document.
    """
    bases = [
        x for x in document.findall(".//base")
        if x.get("href") is not None
    ]
    if not bases:
        return page_url
    parsed_url = bases[0].get("href")
    if parsed_url:
        return parsed_url
    return page_url


URL_CLEAN_RE = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)


def _clean_url(url):
    """Makes sure a URL is fully encoded.  That is, if a ' ' shows up
    in the URL, it will be rewritten to %20 (while not over-quoting
    % or other characters)."""
    return URL_CLEAN_RE.sub(lambda match: '%%%2x' % ord(match.group(0)), url)


def _iter_anchor_data(document, base_url):
    for anchor in document.findall(".//a"):
        href = anchor.get("href")
        if not href:
            continue
        text = anchor.text
        url = _clean_url(six.moves.urllib_parse.urljoin(base_url, href))
        requires_python = unescape(anchor.get("data-requires-python", ""))
        gpg_sig = unescape(anchor.get("data-gpg-sig", ""))
        yield (text, url, requires_python, gpg_sig)


def parse_from_html(html, page_url):
    """Parse anchor data from HTML source.

    `html` should be valid HTML 5 content. This could be either text, or a
    2-tuple of (content, encoding). In the latter case, content would be
    binary, and the encoding is passed into html5lib as transport encoding to
    guess the document's encoding. The transport encoding can be `None` if
    the callee does not have this information.

    `page_url` is the URL pointing to this page. This will be taken into
    account when resolving href values into full URLs.
    """
    kwargs = {"namespaceHTMLElements": False}
    if not isinstance(html, six.string_types):
        html, kwargs["transport_encoding"] = html
    document = html5lib.parse(html, **kwargs)
    base_url = _parse_base_url(document, page_url)
    return _iter_anchor_data(document, base_url)
