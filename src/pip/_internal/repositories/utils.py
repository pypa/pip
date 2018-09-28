#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cgi


def get_content_type_encoding(headers):
    """Parse the encoding information from HTTP headers.

    The charset part of the `Content-Type` header is returned, or None of
    there is none present.

    :param headers: A dict-like mapping, or None.
    """
    if headers and "Content-Type" in headers:
        content_type, params = cgi.parse_header(headers["Content-Type"])
        if "charset" in params:
            return params['charset']
    return None
