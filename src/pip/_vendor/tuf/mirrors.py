#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  mirrors.py

<Author>
  Konstantin Andrianov.
  Derived from original mirrors.py written by Geremy Condra.

<Started>
  March 12, 2012.

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  Extract a list of mirror urls corresponding to the file type and the location
  of the file with respect to the base url.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from pip._vendor import tuf
class _Dummy(object):
  pass
tuf = _Dummy()
from pip._vendor.tuf import formats as _tuf_formats
tuf.formats = _tuf_formats

securesystemslib = _Dummy()
from pip._vendor.securesystemslib import util as _securesystemslib_util
securesystemslib.util = _securesystemslib_util
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions

from pip._vendor import six

# The type of file to be downloaded from a repository.  The
# 'get_list_of_mirrors' function supports these file types.
_SUPPORTED_FILE_TYPES = ['meta', 'target']


def get_list_of_mirrors(file_type, file_path, mirrors_dict):
  """
  <Purpose>
    Get a list of mirror urls from a mirrors dictionary, provided the type
    and the path of the file with respect to the base url.

  <Arguments>
    file_type:
      Type of data needed for download, must correspond to one of the strings
      in the list ['meta', 'target'].  'meta' for metadata file type or
      'target' for target file type.  It should correspond to
      NAME_SCHEMA format.

    file_path:
      A relative path to the file that corresponds to RELPATH_SCHEMA format.
      Ex: 'http://url_prefix/targets_path/file_path'

    mirrors_dict:
      A mirrors_dict object that corresponds to MIRRORDICT_SCHEMA, where
      keys are strings and values are MIRROR_SCHEMA. An example format
      of MIRROR_SCHEMA:

      {'url_prefix': 'http://localhost:8001',
       'metadata_path': 'metadata/',
       'targets_path': 'targets/',
       'confined_target_dirs': ['targets/snapshot1/', ...],
       'custom': {...}}

      The 'custom' field is optional.

  <Exceptions>
    securesystemslib.exceptions.Error, on unsupported 'file_type'.

    securesystemslib.exceptions.FormatError, on bad argument.

  <Return>
    List of mirror urls corresponding to the file_type and file_path.  If no
    match is found, empty list is returned.
  """

  # Checking if all the arguments have appropriate format.
  tuf.formats.RELPATH_SCHEMA.check_match(file_path)
  tuf.formats.MIRRORDICT_SCHEMA.check_match(mirrors_dict)
  securesystemslib.formats.NAME_SCHEMA.check_match(file_type)

  # Verify 'file_type' is supported.
  if file_type not in _SUPPORTED_FILE_TYPES:
    raise securesystemslib.exceptions.Error('Invalid file_type argument.'
      '  Supported file types: ' + repr(_SUPPORTED_FILE_TYPES))
  path_key = 'metadata_path' if file_type == 'meta' else 'targets_path'

  # Reference to 'securesystemslib.util.file_in_confined_directories()' (improve
  # readability).  This function checks whether a mirror should serve a file to
  # the client.  A client may be confined to certain paths on a repository
  # mirror when fetching target files.  This field may be set by the client
  # when the repository mirror is added to the 'tuf.client.updater.Updater'
  # object.
  in_confined_directory = securesystemslib.util.file_in_confined_directories

  list_of_mirrors = []
  for junk, mirror_info in six.iteritems(mirrors_dict):
    # Does mirror serve this file type at all?
    path = mirror_info.get(path_key)
    if path is None:
      continue

    # for targets, ensure directory confinement
    if path_key == 'targets_path':
      full_filepath = os.path.join(path, file_path)
      confined_target_dirs = mirror_info.get('confined_target_dirs')
      # confined_target_dirs is an optional field
      if confined_target_dirs and not in_confined_directory(full_filepath,
          confined_target_dirs):
        continue

    # urllib.quote(string) replaces special characters in string using the %xx
    # escape.  This is done to avoid parsing issues of the URL on the server
    # side. Do *NOT* pass URLs with Unicode characters without first encoding
    # the URL as UTF-8. We need a long-term solution with #61.
    # http://bugs.python.org/issue1712522
    file_path = six.moves.urllib.parse.quote(file_path)
    url = os.path.join(mirror_info['url_prefix'], path, file_path)

    # The above os.path.join() result as well as input file_path may be
    # invalid on windows (might contain both separator types), see #1077.
    # Make sure the URL doesn't contain backward slashes on Windows.
    list_of_mirrors.append(url.replace('\\', '/'))

  return list_of_mirrors
