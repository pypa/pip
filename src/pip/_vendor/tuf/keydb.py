#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  keydb.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  March 21, 2012.  Based on a previous version of this module by Geremy Condra.

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  Represent a collection of keys and their organization.  This module ensures
  the layout of the collection remain consistent and easily verifiable.
  Provided are functions to add and delete keys from the database, retrieve a
  single key, and assemble a collection from keys stored in TUF 'Root' Metadata.
  The Update Framework process maintains a set of role info for multiple
  repositories.

  RSA keys are currently supported and a collection of keys is organized as a
  dictionary indexed by key ID.  Key IDs are used as identifiers for keys
  (e.g., RSA key).  They are the hexadecimal representations of the hash of key
  objects (specifically, the key object containing only the public key).  See
  'rsa_key.py' and the '_get_keyid()' function to learn precisely how keyids
  are generated.  One may get the keyid of a key object by simply accessing the
  dictionary's 'keyid' key (i.e., rsakey['keyid']).
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import copy

class _Dummy(object):
  pass
tuf = _Dummy()
from pip._vendor.tuf import exceptions as _tuf_exceptions
tuf.exceptions = _tuf_exceptions
from pip._vendor.tuf import formats as _tuf_formats
tuf.formats = _tuf_formats

from pip._vendor import six

securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import keys as _securesystemslib_keys
securesystemslib.keys = _securesystemslib_keys

# List of strings representing the key types supported by TUF.
_SUPPORTED_KEY_TYPES = ['rsa', 'ed25519', 'ecdsa-sha2-nistp256']

# See 'log.py' to learn how logging is handled in TUF.
logger = logging.getLogger(__name__)

# The key database.
_keydb_dict = {}
_keydb_dict['default'] = {}


def create_keydb_from_root_metadata(root_metadata, repository_name='default'):
  """
  <Purpose>
    Populate the key database with the unique keys found in 'root_metadata'.
    The database dictionary will conform to
    'tuf.formats.KEYDB_SCHEMA' and have the form: {keyid: key,
    ...}.  The 'keyid' conforms to 'securesystemslib.formats.KEYID_SCHEMA' and
    'key' to its respective type.  In the case of RSA keys, this object would
    match 'RSAKEY_SCHEMA'.

  <Arguments>
    root_metadata:
      A dictionary conformant to 'tuf.formats.ROOT_SCHEMA'.  The keys found
      in the 'keys' field of 'root_metadata' are needed by this function.

    repository_name:
      The name of the repository to store the key information.  If not supplied,
      the key database is populated for the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'root_metadata' does not have the correct format.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not exist in the key
    database.

  <Side Effects>
    A function to add the key to the database is called.  In the case of RSA
    keys, this function is add_key().

    The old keydb key database is replaced.

  <Returns>
    None.
  """

  # Does 'root_metadata' have the correct format?
  # This check will ensure 'root_metadata' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  tuf.formats.ROOT_SCHEMA.check_match(root_metadata)

  # Does 'repository_name' have the correct format?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Clear the key database for 'repository_name', or create it if non-existent.
  if repository_name in _keydb_dict:
    _keydb_dict[repository_name].clear()

  else:
    create_keydb(repository_name)

  # Iterate the keys found in 'root_metadata' by converting them to
  # 'RSAKEY_SCHEMA' if their type is 'rsa', and then adding them to the
  # key database using the provided keyid.
  for keyid, key_metadata in six.iteritems(root_metadata['keys']):
    if key_metadata['keytype'] in _SUPPORTED_KEY_TYPES:
      # 'key_metadata' is stored in 'KEY_SCHEMA' format.  Call
      # create_from_metadata_format() to get the key in 'RSAKEY_SCHEMA' format,
      # which is the format expected by 'add_key()'.  Note: This call to
      # format_metadata_to_key() uses the provided keyid as the default keyid.
      # All other keyids returned are ignored.

      key_dict, _ = securesystemslib.keys.format_metadata_to_key(key_metadata,
          keyid)

      # Make sure to update key_dict['keyid'] to use one of the other valid
      # keyids, otherwise add_key() will have no reference to it.
      try:
        add_key(key_dict, repository_name=repository_name)

      # Although keyid duplicates should *not* occur (unique dict keys), log a
      # warning and continue.  However, 'key_dict' may have already been
      # adding to the keydb elsewhere.
      except tuf.exceptions.KeyAlreadyExistsError as e: # pragma: no cover
        logger.warning(e)
        continue

    else:
      logger.warning('Root Metadata file contains a key with an invalid keytype.')





def create_keydb(repository_name):
  """
  <Purpose>
    Create a key database for a non-default repository named 'repository_name'.

  <Arguments>
    repository_name:
      The name of the repository.  An empty key database is created, and keys
      may be added to via add_key(keyid, repository_name).

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' already exists.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Is 'repository_name' properly formatted?  Raise 'securesystemslib.exceptions.FormatError' if not.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  if repository_name in _keydb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name already exists:'
      ' ' + repr(repository_name))

  _keydb_dict[repository_name] = {}





def remove_keydb(repository_name):
  """
  <Purpose>
    Remove a key database for a non-default repository named 'repository_name'.
    The 'default' repository cannot be removed.

  <Arguments>
    repository_name:
      The name of the repository to remove.  The 'default' repository should
      not be removed, so 'repository_name' cannot be 'default'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' is 'default'.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Is 'repository_name' properly formatted?  Raise 'securesystemslib.exceptions.FormatError' if not.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  if repository_name not in _keydb_dict:
    logger.warning('Repository name does not exist: ' + repr(repository_name))
    return

  if repository_name == 'default':
    raise securesystemslib.exceptions.InvalidNameError('Cannot remove the default repository:'
      ' ' + repr(repository_name))

  del _keydb_dict[repository_name]




def add_key(key_dict, keyid=None, repository_name='default'):
  """
  <Purpose>
    Add 'rsakey_dict' to the key database while avoiding duplicates.
    If keyid is provided, verify it is the correct keyid for 'rsakey_dict'
    and raise an exception if it is not.

  <Arguments>
    key_dict:
      A dictionary conformant to 'securesystemslib.formats.ANYKEY_SCHEMA'.
      It has the form:

      {'keytype': 'rsa',
       'keyid': keyid,
       'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                  'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

    keyid:
      An object conformant to 'KEYID_SCHEMA'.  It is used as an identifier
      for RSA keys.

    repository_name:
      The name of the repository to add the key.  If not supplied, the key is
      added to the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the correct format.

    securesystemslib.exceptions.Error, if 'keyid' does not match the keyid for 'rsakey_dict'.

    tuf.exceptions.KeyAlreadyExistsError, if 'rsakey_dict' is found in the key database.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not exist in the key
    database.

  <Side Effects>
    The keydb key database is modified.

  <Returns>
    None.
  """

  # Does 'key_dict' have the correct format?
  # This check will ensure 'key_dict' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError if the check fails.
  securesystemslib.formats.ANYKEY_SCHEMA.check_match(key_dict)

  # Does 'repository_name' have the correct format?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Does 'keyid' have the correct format?
  if keyid is not None:
    # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
    securesystemslib.formats.KEYID_SCHEMA.check_match(keyid)

    # Check if each keyid found in 'key_dict' matches 'keyid'.
    if keyid != key_dict['keyid']:
      raise securesystemslib.exceptions.Error('Incorrect keyid.  Got ' + key_dict['keyid'] + ' but expected ' + keyid)

  # Ensure 'repository_name' is actually set in the key database.
  if repository_name not in _keydb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not exist:'
      ' ' + repr(repository_name))

  # Check if the keyid belonging to 'key_dict' is not already
  # available in the key database before returning.
  keyid = key_dict['keyid']
  if keyid in _keydb_dict[repository_name]:
    raise tuf.exceptions.KeyAlreadyExistsError('Key: ' + keyid)

  _keydb_dict[repository_name][keyid] = copy.deepcopy(key_dict)





def get_key(keyid, repository_name='default'):
  """
  <Purpose>
    Return the key belonging to 'keyid'.

  <Arguments>
    keyid:
      An object conformant to 'securesystemslib.formats.KEYID_SCHEMA'.  It is used as an
      identifier for keys.

    repository_name:
      The name of the repository to get the key.  If not supplied, the key is
      retrieved from the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the correct format.

    tuf.exceptions.UnknownKeyError, if 'keyid' is not found in the keydb database.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not exist in the key
    database.

  <Side Effects>
    None.

  <Returns>
    The key matching 'keyid'.  In the case of RSA keys, a dictionary conformant
    to 'securesystemslib.formats.RSAKEY_SCHEMA' is returned.
  """

  # Does 'keyid' have the correct format?
  # This check will ensure 'keyid' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' is the match fails.
  securesystemslib.formats.KEYID_SCHEMA.check_match(keyid)

  # Does 'repository_name' have the correct format?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  if repository_name not in _keydb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not exist:'
      ' ' + repr(repository_name))

  # Return the key belonging to 'keyid', if found in the key database.
  try:
    return copy.deepcopy(_keydb_dict[repository_name][keyid])

  except KeyError as error:
    six.raise_from(tuf.exceptions.UnknownKeyError('Key: ' + keyid), error)





def remove_key(keyid, repository_name='default'):
  """
  <Purpose>
    Remove the key belonging to 'keyid'.

  <Arguments>
    keyid:
      An object conformant to 'securesystemslib.formats.KEYID_SCHEMA'.  It is used as an
      identifier for keys.

    repository_name:
      The name of the repository to remove the key.  If not supplied, the key
      is removed from the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the correct format.

    tuf.exceptions.UnknownKeyError, if 'keyid' is not found in key database.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not exist in the key
    database.

  <Side Effects>
    The key, identified by 'keyid', is deleted from the key database.

  <Returns>
    None.
  """

  # Does 'keyid' have the correct format?
  # This check will ensure 'keyid' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' is the match fails.
  securesystemslib.formats.KEYID_SCHEMA.check_match(keyid)

  # Does 'repository_name' have the correct format?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  if repository_name not in _keydb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not exist:'
      ' ' + repr(repository_name))

  # Remove the key belonging to 'keyid' if found in the key database.
  if keyid in _keydb_dict[repository_name]:
    del _keydb_dict[repository_name][keyid]

  else:
    raise tuf.exceptions.UnknownKeyError('Key: ' + keyid)





def clear_keydb(repository_name='default', clear_all=False):

  """
  <Purpose>
    Clear the keydb key database.

  <Arguments>
    repository_name:
      The name of the repository to clear the key database.  If not supplied,
      the key database is cleared for the 'default' repository.

    clear_all:
      Boolean indicating whether to clear the entire keydb.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not exist in the key
    database.

  <Side Effects>
    The keydb key database is reset.

  <Returns>
    None.
  """

  # Do the arguments have the correct format?  Raise 'securesystemslib.exceptions.FormatError' if
  # 'repository_name' is improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)
  securesystemslib.formats.BOOLEAN_SCHEMA.check_match(clear_all)

  global _keydb_dict

  if clear_all:
    _keydb_dict = {}
    _keydb_dict['default'] = {}

  if repository_name not in _keydb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not exist:'
      ' ' + repr(repository_name))

  _keydb_dict[repository_name] = {}
