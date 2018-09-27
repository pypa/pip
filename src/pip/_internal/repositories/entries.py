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
