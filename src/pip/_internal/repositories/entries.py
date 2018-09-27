#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

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


def parse_base_url(document, page_url):
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
