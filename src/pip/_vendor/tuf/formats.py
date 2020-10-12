#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  formats.py

<Author>
  Geremy Condra
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  Refactored April 30, 2012. -vladimir.v.diaz

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  A central location for all format-related checking of TUF objects.
  Some crypto-related formats may also be defined in securesystemslib.
  Note: 'formats.py' depends heavily on 'schema.py', so the 'schema.py'
  module should be read and understood before tackling this module.

  'formats.py' can be broken down into two sections.  (1) Schemas and object
  matching.  (2) Functions that help produce or verify TUF objects.

  The first section deals with schemas and object matching based on format.
  There are two ways of checking the format of objects.  The first method
  raises a 'securesystemslib.exceptions.FormatError' exception if the match
  fails and the other returns a Boolean result.

  tuf.formats.<SCHEMA>.check_match(object)
  tuf.formats.<SCHEMA>.matches(object)

  Example:

  rsa_key = {'keytype': 'rsa'
             'keyid': 34892fc465ac76bc3232fab
             'keyval': {'public': 'public_key',
                        'private': 'private_key'}

  securesystemslib.formats.RSAKEY_SCHEMA.check_match(rsa_key)
  securesystemslib.formats.RSAKEY_SCHEMA.matches(rsa_key)

  In this example, if a dict key or dict value is missing or incorrect,
  the match fails.  There are numerous variations of object checking
  provided by 'formats.py' and 'schema.py'.

  The second section contains miscellaneous functions related to the format of
  TUF objects.
  Example:

  signable_object = make_signable(unsigned_object)
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import calendar
import datetime
import time
import copy

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats

from pip._vendor.securesystemslib import schema as SCHEMA

from pip._vendor import tuf

from pip._vendor import six

# As per TUF spec 1.0.0 the spec version field must follow the Semantic
# Versioning 2.0.0 (semver) format. The regex pattern is provided by semver.
# https://semver.org/spec/v2.0.0.html#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_2_0_0_SCHEMA = SCHEMA.RegularExpression(
    r'(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
    r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
    r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
    r'(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?'
)
SPECIFICATION_VERSION_SCHEMA = SCHEMA.OneOf([
    # However, temporarily allow "1.0" for backwards-compatibility in tuf-0.12.PATCH.
    SCHEMA.String("1.0"),
    SEMVER_2_0_0_SCHEMA
])

# A datetime in 'YYYY-MM-DDTHH:MM:SSZ' ISO 8601 format.  The "Z" zone designator
# for the zero UTC offset is always used (i.e., a numerical offset is not
# supported.)  Example: '2015-10-21T13:20:00Z'.  Note:  This is a simple format
# check, and an ISO8601 string should be fully verified when it is parsed.
ISO8601_DATETIME_SCHEMA = SCHEMA.RegularExpression(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')

# An integer representing the numbered version of a metadata file.
# Must be 1, or greater.
METADATAVERSION_SCHEMA = SCHEMA.Integer(lo=0)

# A relative file path (e.g., 'metadata/root/').
RELPATH_SCHEMA = SCHEMA.AnyString()
RELPATHS_SCHEMA = SCHEMA.ListOf(RELPATH_SCHEMA)

VERSIONINFO_SCHEMA = SCHEMA.Object(
  object_name = 'VERSIONINFO_SCHEMA',
  version = METADATAVERSION_SCHEMA)

# A string representing a role's name.
ROLENAME_SCHEMA = SCHEMA.AnyString()

# A role's threshold value (i.e., the minimum number
# of signatures required to sign a metadata file).
# Must be 1 and greater.
THRESHOLD_SCHEMA = SCHEMA.Integer(lo=1)

# A hexadecimal value in '23432df87ab..' format.
HEX_SCHEMA = SCHEMA.RegularExpression(r'[a-fA-F0-9]+')

# A path hash prefix is a hexadecimal string.
PATH_HASH_PREFIX_SCHEMA = HEX_SCHEMA

# A list of path hash prefixes.
PATH_HASH_PREFIXES_SCHEMA = SCHEMA.ListOf(PATH_HASH_PREFIX_SCHEMA)

# Role object in {'keyids': [keydids..], 'name': 'ABC', 'threshold': 1,
# 'paths':[filepaths..]} format.
# TODO: This is not a role.  In further #660-related PRs, fix it, similar to
#       the way I did in Uptane's TUF fork.
ROLE_SCHEMA = SCHEMA.Object(
  object_name = 'ROLE_SCHEMA',
  name = SCHEMA.Optional(ROLENAME_SCHEMA),
  keyids = securesystemslib.formats.KEYIDS_SCHEMA,
  threshold = THRESHOLD_SCHEMA,
  terminating = SCHEMA.Optional(securesystemslib.formats.BOOLEAN_SCHEMA),
  paths = SCHEMA.Optional(RELPATHS_SCHEMA),
  path_hash_prefixes = SCHEMA.Optional(PATH_HASH_PREFIXES_SCHEMA))

# A dict of roles where the dict keys are role names and the dict values holding
# the role data/information.
ROLEDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = ROLENAME_SCHEMA,
  value_schema = ROLE_SCHEMA)

# A dictionary of ROLEDICT, where dictionary keys can be repository names, and
# dictionary values containing information for each role available on the
# repository (corresponding to the repository belonging to named repository in
# the dictionary key)
ROLEDICTDB_SCHEMA = SCHEMA.DictOf(
  key_schema = securesystemslib.formats.NAME_SCHEMA,
  value_schema = ROLEDICT_SCHEMA)

# Command argument list, as used by the CLI tool.
# Example: {'keytype': ed25519, 'expires': 365,}
COMMAND_SCHEMA = SCHEMA.DictOf(
  key_schema = securesystemslib.formats.NAME_SCHEMA,
  value_schema = SCHEMA.Any())

# A dictionary holding version information.
VERSION_SCHEMA = SCHEMA.Object(
  object_name = 'VERSION_SCHEMA',
  major = SCHEMA.Integer(lo=0),
  minor = SCHEMA.Integer(lo=0),
  fix = SCHEMA.Integer(lo=0))

# A value that is either True or False, on or off, etc.
BOOLEAN_SCHEMA = SCHEMA.Boolean()

# A hexadecimal value in '23432df87ab..' format.
HASH_SCHEMA = SCHEMA.RegularExpression(r'[a-fA-F0-9]+')

# A key identifier (e.g., a hexadecimal value identifying an RSA key).
KEYID_SCHEMA = HASH_SCHEMA

# A list of KEYID_SCHEMA.
KEYIDS_SCHEMA = SCHEMA.ListOf(KEYID_SCHEMA)

# The actual values of a key, as opposed to meta data such as a key type and
# key identifier ('rsa', 233df889cb).  For RSA keys, the key value is a pair of
# public and private keys in PEM Format stored as strings.
KEYVAL_SCHEMA = SCHEMA.Object(
  object_name = 'KEYVAL_SCHEMA',
  public = SCHEMA.AnyString(),
  private = SCHEMA.Optional(SCHEMA.AnyString()))

# A generic TUF key.  All TUF keys should be saved to metadata files in this
# format.
KEY_SCHEMA = SCHEMA.Object(
  object_name = 'KEY_SCHEMA',
  keytype = SCHEMA.AnyString(),
  keyval = KEYVAL_SCHEMA,
  expires = SCHEMA.Optional(ISO8601_DATETIME_SCHEMA))

# A dict where the dict keys hold a keyid and the dict values a key object.
KEYDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = KEYID_SCHEMA,
  value_schema = KEY_SCHEMA)

# The format used by the key database to store keys.  The dict keys hold a key
# identifier and the dict values any object.  The key database should store
# key objects in the values (e.g., 'RSAKEY_SCHEMA', 'DSAKEY_SCHEMA').
KEYDB_SCHEMA = SCHEMA.DictOf(
  key_schema = KEYID_SCHEMA,
  value_schema = SCHEMA.Any())

# A schema holding the result of checking the signatures of a particular
# 'SIGNABLE_SCHEMA' role.
# For example, how many of the signatures for the 'Target' role are
# valid?  This SCHEMA holds this information.  See 'sig.py' for
# more information.
SIGNATURESTATUS_SCHEMA = SCHEMA.Object(
  object_name = 'SIGNATURESTATUS_SCHEMA',
  threshold = SCHEMA.Integer(),
  good_sigs = KEYIDS_SCHEMA,
  bad_sigs = KEYIDS_SCHEMA,
  unknown_sigs = KEYIDS_SCHEMA,
  untrusted_sigs = KEYIDS_SCHEMA)

# An integer representing length.  Must be 0, or greater.
LENGTH_SCHEMA = SCHEMA.Integer(lo=0)

# A dict in {'sha256': '23432df87ab..', 'sha512': '34324abc34df..', ...} format.
HASHDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = SCHEMA.AnyString(),
  value_schema = HASH_SCHEMA)

# Information about target files, like file length and file hash(es).  This
# schema allows the storage of multiple hashes for the same file (e.g., sha256
# and sha512 may be computed for the same file and stored).
TARGETS_FILEINFO_SCHEMA = SCHEMA.Object(
  object_name = 'TARGETS_FILEINFO_SCHEMA',
  length = LENGTH_SCHEMA,
  hashes = HASHDICT_SCHEMA,
  custom = SCHEMA.Optional(SCHEMA.Object()))

# Information about snapshot and timestamp files. This schema allows for optional
# length and hashes, but version is mandatory.
METADATA_FILEINFO_SCHEMA = SCHEMA.Object(
  object_name = 'METADATA_FILEINFO_SCHEMA',
  length = SCHEMA.Optional(LENGTH_SCHEMA),
  hashes = SCHEMA.Optional(HASHDICT_SCHEMA),
  version = METADATAVERSION_SCHEMA)

# A dict holding the version or file information for a particular metadata
# role.  The dict keys hold the relative file paths, and the dict values the
# corresponding version numbers and/or file information.
FILEINFODICT_SCHEMA = SCHEMA.DictOf(
  key_schema = RELPATH_SCHEMA,
  value_schema = SCHEMA.OneOf([VERSIONINFO_SCHEMA,
                              METADATA_FILEINFO_SCHEMA]))

# A dict holding the information for a particular target / file.  The dict keys
# hold the relative file paths, and the dict values the corresponding file
# information.
FILEDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = RELPATH_SCHEMA,
  value_schema = TARGETS_FILEINFO_SCHEMA)

# A dict holding a target info.
TARGETINFO_SCHEMA = SCHEMA.Object(
  object_name = 'TARGETINFO_SCHEMA',
  filepath = RELPATH_SCHEMA,
  fileinfo = TARGETS_FILEINFO_SCHEMA)

# A list of TARGETINFO_SCHEMA.
TARGETINFOS_SCHEMA = SCHEMA.ListOf(TARGETINFO_SCHEMA)

# A string representing a named oject.
NAME_SCHEMA = SCHEMA.AnyString()

# A dict of repository names to mirrors.
REPO_NAMES_TO_MIRRORS_SCHEMA = SCHEMA.DictOf(
  key_schema = NAME_SCHEMA,
  value_schema = SCHEMA.ListOf(securesystemslib.formats.URL_SCHEMA))

# An object containing the map file's "mapping" attribute.
MAPPING_SCHEMA = SCHEMA.ListOf(SCHEMA.Object(
  paths = RELPATHS_SCHEMA,
  repositories = SCHEMA.ListOf(NAME_SCHEMA),
  terminating = BOOLEAN_SCHEMA,
  threshold = THRESHOLD_SCHEMA))

# A dict containing the map file (named 'map.json', by default).  The format of
# the map file is covered in TAP 4: Multiple repository consensus on entrusted
# targets.
MAPFILE_SCHEMA = SCHEMA.Object(
  repositories = REPO_NAMES_TO_MIRRORS_SCHEMA,
  mapping = MAPPING_SCHEMA)

# Like ROLEDICT_SCHEMA, except that ROLE_SCHEMA instances are stored in order.
ROLELIST_SCHEMA = SCHEMA.ListOf(ROLE_SCHEMA)

# The delegated roles of a Targets role (a parent).
DELEGATIONS_SCHEMA = SCHEMA.Object(
  keys = KEYDICT_SCHEMA,
  roles = ROLELIST_SCHEMA)

# The number of hashed bins, or the number of delegated roles.  See
# delegate_hashed_bins() in 'repository_tool.py' for an example.  Note:
# Tools may require further restrictions on the number of bins, such
# as requiring them to be a power of 2.
NUMBINS_SCHEMA = SCHEMA.Integer(lo=1)

# The fileinfo format of targets specified in the repository and
# developer tools.  The fields match that of TARGETS_FILEINFO_SCHEMA, only all
# fields are optional.
CUSTOM_SCHEMA = SCHEMA.DictOf(
  key_schema = SCHEMA.AnyString(),
  value_schema = SCHEMA.Any()
)
LOOSE_TARGETS_FILEINFO_SCHEMA = SCHEMA.Object(
  object_name = "LOOSE_TARGETS_FILEINFO_SCHEMA",
  length = SCHEMA.Optional(LENGTH_SCHEMA),
  hashes = SCHEMA.Optional(HASHDICT_SCHEMA),
  version = SCHEMA.Optional(METADATAVERSION_SCHEMA),
  custom = SCHEMA.Optional(SCHEMA.Object())
)

PATH_FILEINFO_SCHEMA = SCHEMA.DictOf(
  key_schema = RELPATH_SCHEMA,
  value_schema = LOOSE_TARGETS_FILEINFO_SCHEMA)

# TUF roledb
ROLEDB_SCHEMA = SCHEMA.Object(
  object_name = 'ROLEDB_SCHEMA',
  keyids = SCHEMA.Optional(KEYIDS_SCHEMA),
  signing_keyids = SCHEMA.Optional(KEYIDS_SCHEMA),
  previous_keyids = SCHEMA.Optional(KEYIDS_SCHEMA),
  threshold = SCHEMA.Optional(THRESHOLD_SCHEMA),
  previous_threshold = SCHEMA.Optional(THRESHOLD_SCHEMA),
  version = SCHEMA.Optional(METADATAVERSION_SCHEMA),
  expires = SCHEMA.Optional(ISO8601_DATETIME_SCHEMA),
  signatures = SCHEMA.Optional(securesystemslib.formats.SIGNATURES_SCHEMA),
  paths = SCHEMA.Optional(SCHEMA.OneOf([RELPATHS_SCHEMA, PATH_FILEINFO_SCHEMA])),
  path_hash_prefixes = SCHEMA.Optional(PATH_HASH_PREFIXES_SCHEMA),
  delegations = SCHEMA.Optional(DELEGATIONS_SCHEMA),
  partial_loaded = SCHEMA.Optional(BOOLEAN_SCHEMA))

# A signable object.  Holds the signing role and its associated signatures.
SIGNABLE_SCHEMA = SCHEMA.Object(
  object_name = 'SIGNABLE_SCHEMA',
  signed = SCHEMA.Any(),
  signatures = SCHEMA.ListOf(securesystemslib.formats.SIGNATURE_SCHEMA))

# Root role: indicates root keys and top-level roles.
ROOT_SCHEMA = SCHEMA.Object(
  object_name = 'ROOT_SCHEMA',
  _type = SCHEMA.String('root'),
  spec_version = SPECIFICATION_VERSION_SCHEMA,
  version = METADATAVERSION_SCHEMA,
  consistent_snapshot = BOOLEAN_SCHEMA,
  expires = ISO8601_DATETIME_SCHEMA,
  keys = KEYDICT_SCHEMA,
  roles = ROLEDICT_SCHEMA)

# Targets role: Indicates targets and delegates target paths to other roles.
TARGETS_SCHEMA = SCHEMA.Object(
  object_name = 'TARGETS_SCHEMA',
  _type = SCHEMA.String('targets'),
  spec_version = SPECIFICATION_VERSION_SCHEMA,
  version = METADATAVERSION_SCHEMA,
  expires = ISO8601_DATETIME_SCHEMA,
  targets = FILEDICT_SCHEMA,
  delegations = SCHEMA.Optional(DELEGATIONS_SCHEMA))

# Snapshot role: indicates the latest versions of all metadata (except
# timestamp).
SNAPSHOT_SCHEMA = SCHEMA.Object(
  object_name = 'SNAPSHOT_SCHEMA',
  _type = SCHEMA.String('snapshot'),
  version = METADATAVERSION_SCHEMA,
  expires = securesystemslib.formats.ISO8601_DATETIME_SCHEMA,
  spec_version = SPECIFICATION_VERSION_SCHEMA,
  meta = FILEINFODICT_SCHEMA)

# Timestamp role: indicates the latest version of the snapshot file.
TIMESTAMP_SCHEMA = SCHEMA.Object(
  object_name = 'TIMESTAMP_SCHEMA',
  _type = SCHEMA.String('timestamp'),
  spec_version = SPECIFICATION_VERSION_SCHEMA,
  version = METADATAVERSION_SCHEMA,
  expires = securesystemslib.formats.ISO8601_DATETIME_SCHEMA,
  meta = FILEINFODICT_SCHEMA)


# project.cfg file: stores information about the project in a json dictionary
PROJECT_CFG_SCHEMA = SCHEMA.Object(
    object_name = 'PROJECT_CFG_SCHEMA',
    project_name = SCHEMA.AnyString(),
    layout_type = SCHEMA.OneOf([SCHEMA.String('repo-like'), SCHEMA.String('flat')]),
    targets_location = securesystemslib.formats.PATH_SCHEMA,
    metadata_location = securesystemslib.formats.PATH_SCHEMA,
    prefix = securesystemslib.formats.PATH_SCHEMA,
    public_keys = securesystemslib.formats.KEYDICT_SCHEMA,
    threshold = SCHEMA.Integer(lo = 0, hi = 2)
    )

# A schema containing information a repository mirror may require,
# such as a url, the path of the directory metadata files, etc.
MIRROR_SCHEMA = SCHEMA.Object(
  object_name = 'MIRROR_SCHEMA',
  url_prefix = securesystemslib.formats.URL_SCHEMA,
  metadata_path = SCHEMA.Optional(RELPATH_SCHEMA),
  targets_path = SCHEMA.Optional(RELPATH_SCHEMA),
  confined_target_dirs = SCHEMA.Optional(RELPATHS_SCHEMA),
  custom = SCHEMA.Optional(SCHEMA.Object()))

# A dictionary of mirrors where the dict keys hold the mirror's name and
# and the dict values the mirror's data (i.e., 'MIRROR_SCHEMA').
# The repository class of 'updater.py' accepts dictionaries
# of this type provided by the TUF client.
MIRRORDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = SCHEMA.AnyString(),
  value_schema = MIRROR_SCHEMA)

# A Mirrorlist: indicates all the live mirrors, and what documents they
# serve.
MIRRORLIST_SCHEMA = SCHEMA.Object(
  object_name = 'MIRRORLIST_SCHEMA',
  _type = SCHEMA.String('mirrors'),
  version = METADATAVERSION_SCHEMA,
  expires = securesystemslib.formats.ISO8601_DATETIME_SCHEMA,
  mirrors = SCHEMA.ListOf(MIRROR_SCHEMA))

# Any of the role schemas (e.g., TIMESTAMP_SCHEMA, SNAPSHOT_SCHEMA, etc.)
ANYROLE_SCHEMA = SCHEMA.OneOf([ROOT_SCHEMA, TARGETS_SCHEMA, SNAPSHOT_SCHEMA,
                               TIMESTAMP_SCHEMA, MIRROR_SCHEMA])

# The format of the resulting "scp config dict" after extraction from the
# push configuration file (i.e., push.cfg).  In the case of a config file
# utilizing the scp transfer module, it must contain the 'general' and 'scp'
# sections, where 'general' must contain a 'transfer_module' and
# 'metadata_path' entry, and 'scp' the 'host', 'user', 'identity_file', and
# 'remote_directory' entries.
SCPCONFIG_SCHEMA = SCHEMA.Object(
  object_name = 'SCPCONFIG_SCHEMA',
  general = SCHEMA.Object(
    object_name = '[general]',
    transfer_module = SCHEMA.String('scp'),
    metadata_path = securesystemslib.formats.PATH_SCHEMA,
    targets_directory = securesystemslib.formats.PATH_SCHEMA),
  scp=SCHEMA.Object(
    object_name = '[scp]',
    host = securesystemslib.formats.URL_SCHEMA,
    user = securesystemslib.formats.NAME_SCHEMA,
    identity_file = securesystemslib.formats.PATH_SCHEMA,
    remote_directory = securesystemslib.formats.PATH_SCHEMA))

# The format of the resulting "receive config dict" after extraction from the
# receive configuration file (i.e., receive.cfg).  The receive config file
# must contain a 'general' section, and this section the 'pushroots',
# 'repository_directory', 'metadata_directory', 'targets_directory', and
# 'backup_directory' entries.
RECEIVECONFIG_SCHEMA = SCHEMA.Object(
  object_name = 'RECEIVECONFIG_SCHEMA', general=SCHEMA.Object(
    object_name = '[general]',
    pushroots = SCHEMA.ListOf(securesystemslib.formats.PATH_SCHEMA),
    repository_directory = securesystemslib.formats.PATH_SCHEMA,
    metadata_directory = securesystemslib.formats.PATH_SCHEMA,
    targets_directory = securesystemslib.formats.PATH_SCHEMA,
    backup_directory = securesystemslib.formats.PATH_SCHEMA))



def make_signable(role_schema):
  """
  <Purpose>
    Return the role metadata 'role_schema' in 'SIGNABLE_SCHEMA' format.
    'role_schema' is added to the 'signed' key, and an empty list
    initialized to the 'signatures' key.  The caller adds signatures
    to this second field.
    Note: check_signable_object_format() should be called after
    make_signable() and signatures added to ensure the final
    signable object has a valid format (i.e., a signable containing
    a supported role metadata).

  <Arguments>
    role_schema:
      A role schema dict (e.g., 'ROOT_SCHEMA', 'SNAPSHOT_SCHEMA').

  <Exceptions>
    None.

  <Side Effects>
    None.

  <Returns>
    A dict in 'SIGNABLE_SCHEMA' format.
  """

  if not isinstance(role_schema, dict) or 'signed' not in role_schema:
    return { 'signed' : role_schema, 'signatures' : [] }

  else:
    return role_schema






def build_dict_conforming_to_schema(schema, **kwargs):
  """
  <Purpose>
    Given a schema.Object object (for example, TIMESTAMP_SCHEMA from this
    module) and a set of keyword arguments, create a dictionary that conforms
    to the given schema, using the keyword arguments to define the elements of
    the new dict.

    Checks the result to make sure that it conforms to the given schema, raising
    an error if not.

  <Arguments>
    schema
      A schema.Object, like TIMESTAMP_SCHEMA, TARGETS_FILEINFO_SCHEMA,
      securesystemslib.formats.SIGNATURE_SCHEMA, etc.

    **kwargs
      A keyword argument for each element of the schema.  Optional arguments
      may be included or skipped, but all required arguments must be included.

      For example, for TIMESTAMP_SCHEMA, a call might look like:
        build_dict_conforming_to_schema(
            TIMESTAMP_SCHEMA,
            _type='timestamp',
            spec_version='1.0.0',
            version=1,
            expires='2020-01-01T00:00:00Z',
            meta={...})
      Some arguments will be filled in if excluded: _type, spec_version

  <Returns>
    A dictionary conforming to the given schema.  Adds certain required fields
    if they are missing and can be deduced from the schema.  The data returned
    is a deep copy.

  <Exceptions>
    securesystemslib.exceptions.FormatError
      if the provided data does not match the schema when assembled.

  <Side Effects>
    None.  In particular, the provided values are not modified, and the
    returned dictionary does not include references to them.

  """

  # Check the schema argument type (must provide check_match and _required).
  if not isinstance(schema, SCHEMA.Object):
    raise ValueError(
        'The first argument must be a schema.Object instance, but is not. '
        'Given schema: ' + repr(schema))

  # Make a copy of the provided fields so that the caller's provided values
  # do not change when the returned values are changed.
  dictionary = copy.deepcopy(kwargs)


  # Automatically provide certain schema properties if they are not already
  # provided and are required in objects of class <schema>.
  # This includes:
  #   _type:        <securesystemslib.schema.String object>
  #   spec_version: SPECIFICATION_VERSION_SCHEMA
  #
  # (Please note that _required is slightly misleading, as it includes both
  #  required and optional elements. It should probably be called _components.)
  #
  for key, element_type in schema._required: #pylint: disable=protected-access

    if key in dictionary:
      # If the field has been provided, proceed normally.
      continue

    elif isinstance(element_type, SCHEMA.Optional):
      # If the field has NOT been provided but IS optional, proceed without it.
      continue

    else:
      # If the field has not been provided and is required, check to see if
      # the field is one of the fields we automatically fill.

      # Currently, the list is limited to ['_type', 'spec_version'].

      if key == '_type' and isinstance(element_type, SCHEMA.String):
        # A SCHEMA.String stores its expected value in _string, so use that.
        dictionary[key] = element_type._string #pylint: disable=protected-access

      elif (key == 'spec_version' and
          element_type == SPECIFICATION_VERSION_SCHEMA):
        # If not provided, use the specification version in tuf/__init__.py
        dictionary[key] = tuf.SPECIFICATION_VERSION


  # If what we produce does not match the provided schema, raise a FormatError.
  schema.check_match(dictionary)

  return dictionary





# A dict holding the recognized schemas for the top-level roles.
SCHEMAS_BY_TYPE = {
  'root' : ROOT_SCHEMA,
  'targets' : TARGETS_SCHEMA,
  'snapshot' : SNAPSHOT_SCHEMA,
  'timestamp' : TIMESTAMP_SCHEMA,
  'mirrors' : MIRRORLIST_SCHEMA}




def expiry_string_to_datetime(expires):
  """
  <Purpose>
    Convert an expiry string to a datetime object.
  <Arguments>
    expires:
      The expiry date-time string in the ISO8601 format that is defined
      in securesystemslib.ISO8601_DATETIME_SCHEMA. E.g. '2038-01-19T03:14:08Z'
  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'expires' cannot be
    parsed correctly.
  <Side Effects>
    None.
  <Returns>
    A datetime object representing the expiry time.
  """

  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.ISO8601_DATETIME_SCHEMA.check_match(expires)

  try:
    return datetime.datetime.strptime(expires, "%Y-%m-%dT%H:%M:%SZ")
  except ValueError as error:
    six.raise_from(securesystemslib.exceptions.FormatError(
        'Failed to parse ' + repr(expires) + ' as an expiry time'),
        error)




def datetime_to_unix_timestamp(datetime_object):
  """
  <Purpose>
    Convert 'datetime_object' (in datetime.datetime()) format) to a Unix/POSIX
    timestamp.  For example, Python's time.time() returns a Unix timestamp, and
    includes the number of microseconds.  'datetime_object' is converted to UTC.

    >>> datetime_object = datetime.datetime(1985, 10, 26, 1, 22)
    >>> timestamp = datetime_to_unix_timestamp(datetime_object)
    >>> timestamp
    499137720

  <Arguments>
    datetime_object:
      The datetime.datetime() object to convert to a Unix timestamp.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'datetime_object' is not a
    datetime.datetime() object.

  <Side Effects>
    None.

  <Returns>
    A unix (posix) timestamp (e.g., 499137660).
  """

  # Is 'datetime_object' a datetime.datetime() object?
  # Raise 'securesystemslib.exceptions.FormatError' if not.
  if not isinstance(datetime_object, datetime.datetime):
    message = repr(datetime_object) + ' is not a datetime.datetime() object.'
    raise securesystemslib.exceptions.FormatError(message)

  unix_timestamp = calendar.timegm(datetime_object.timetuple())

  return unix_timestamp





def unix_timestamp_to_datetime(unix_timestamp):
  """
  <Purpose>
    Convert 'unix_timestamp' (i.e., POSIX time, in UNIX_TIMESTAMP_SCHEMA format)
    to a datetime.datetime() object.  'unix_timestamp' is the number of seconds
    since the epoch (January 1, 1970.)

    >>> datetime_object = unix_timestamp_to_datetime(1445455680)
    >>> datetime_object
    datetime.datetime(2015, 10, 21, 19, 28)

  <Arguments>
    unix_timestamp:
      An integer representing the time (e.g., 1445455680).  Conformant to
      'securesystemslib.formats.UNIX_TIMESTAMP_SCHEMA'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'unix_timestamp' is improperly
    formatted.

  <Side Effects>
    None.

  <Returns>
    A datetime.datetime() object corresponding to 'unix_timestamp'.
  """

  # Is 'unix_timestamp' properly formatted?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.UNIX_TIMESTAMP_SCHEMA.check_match(unix_timestamp)

  # Convert 'unix_timestamp' to a 'time.struct_time',  in UTC.  The Daylight
  # Savings Time (DST) flag is set to zero.  datetime.fromtimestamp() is not
  # used because it returns a local datetime.
  struct_time = time.gmtime(unix_timestamp)

  # Extract the (year, month, day, hour, minutes, seconds) arguments for the
  # datetime object to be returned.
  datetime_object = datetime.datetime(*struct_time[:6])

  return datetime_object



def format_base64(data):
  """
  <Purpose>
    Return the base64 encoding of 'data' with whitespace and '=' signs omitted.

  <Arguments>
    data:
      Binary or buffer of data to convert.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the base64 encoding fails or the
    argument is invalid.

  <Side Effects>
    None.

  <Returns>
    A base64-encoded string.
  """

  try:
    return binascii.b2a_base64(data).decode('utf-8').rstrip('=\n ')

  except (TypeError, binascii.Error) as e:
    raise securesystemslib.exceptions.FormatError('Invalid base64'
      ' encoding: ' + str(e))




def parse_base64(base64_string):
  """
  <Purpose>
    Parse a base64 encoding with whitespace and '=' signs omitted.

  <Arguments>
    base64_string:
      A string holding a base64 value.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'base64_string' cannot be parsed
    due to an invalid base64 encoding.

  <Side Effects>
    None.

  <Returns>
    A byte string representing the parsed based64 encoding of
    'base64_string'.
  """

  if not isinstance(base64_string, six.string_types):
    message = 'Invalid argument: '+repr(base64_string)
    raise securesystemslib.exceptions.FormatError(message)

  extra = len(base64_string) % 4
  if extra:
    padding = '=' * (4 - extra)
    base64_string = base64_string + padding

  try:
    return binascii.a2b_base64(base64_string.encode('utf-8'))

  except (TypeError, binascii.Error) as e:
    raise securesystemslib.exceptions.FormatError('Invalid base64'
      ' encoding: ' + str(e))



def make_targets_fileinfo(length, hashes, custom=None):
  """
  <Purpose>
    Create a dictionary conformant to 'TARGETS_FILEINFO_SCHEMA'.
    This dict describes a target file.

  <Arguments>
    length:
      An integer representing the size of the file.

    hashes:
      A dict of hashes in 'HASHDICT_SCHEMA' format, which has the form:
       {'sha256': 123df8a9b12, 'sha512': 324324dfc121, ...}

    custom:
      An optional object providing additional information about the file.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the 'TARGETS_FILEINFO_SCHEMA' to be
    returned does not have the correct format.

  <Returns>
    A dictionary conformant to 'TARGETS_FILEINFO_SCHEMA', representing the file
    information of a target file.
  """

  fileinfo = {'length' : length, 'hashes' : hashes}

  if custom is not None:
    fileinfo['custom'] = custom

  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  TARGETS_FILEINFO_SCHEMA.check_match(fileinfo)

  return fileinfo



def make_metadata_fileinfo(version, length=None, hashes=None):
  """
  <Purpose>
    Create a dictionary conformant to 'METADATA_FILEINFO_SCHEMA'.
    This dict describes one of the metadata files used for timestamp and
    snapshot roles.

  <Arguments>
    version:
      An integer representing the version of the file.

    length:
      An optional integer representing the size of the file.

    hashes:
      An optional dict of hashes in 'HASHDICT_SCHEMA' format, which has the form:
       {'sha256': 123df8a9b12, 'sha512': 324324dfc121, ...}


  <Exceptions>
    securesystemslib.exceptions.FormatError, if the 'METADATA_FILEINFO_SCHEMA' to be
    returned does not have the correct format.

  <Returns>
    A dictionary conformant to 'METADATA_FILEINFO_SCHEMA', representing the file
    information of a metadata file.
  """

  fileinfo = {'version' : version}

  if length:
    fileinfo['length'] = length

  if hashes:
    fileinfo['hashes'] = hashes

  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  METADATA_FILEINFO_SCHEMA.check_match(fileinfo)

  return fileinfo



def make_versioninfo(version_number):
  """
  <Purpose>
    Create a dictionary conformant to 'VERSIONINFO_SCHEMA'.  This dict
    describes both metadata and target files.

  <Arguments>
    version_number:
      An integer representing the version of a particular metadata role.
      The dictionary returned by this function is expected to be included
      in Snapshot metadata.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the dict to be returned does not
    have the correct format (i.e., VERSIONINFO_SCHEMA).

  <Side Effects>
    None.

  <Returns>
    A dictionary conformant to 'VERSIONINFO_SCHEMA', containing the version
    information of a metadata role.
  """

  versioninfo = {'version': version_number}

  # Raise 'securesystemslib.exceptions.FormatError' if 'versioninfo' is
  # improperly formatted.
  VERSIONINFO_SCHEMA.check_match(versioninfo)

  return versioninfo





def expected_meta_rolename(meta_rolename):
  """
  <Purpose>
    Ensure 'meta_rolename' is properly formatted.
    'targets' is returned as 'Targets'.
    'targets role1' is returned as 'Targets Role1'.

    The words in the string (i.e., separated by whitespace)
    are capitalized.

  <Arguments>
    meta_rolename:
      A string representing the rolename.
      E.g., 'root', 'targets'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'meta_rolename' is improperly
    formatted.

  <Side Effects>
    None.

  <Returns>
    A string (e.g., 'Root', 'Targets').
  """

  # Does 'meta_rolename' have the correct type?
  # This check ensures 'meta_rolename' conforms to
  # 'securesystemslib.formats.NAME_SCHEMA'.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.NAME_SCHEMA.check_match(meta_rolename)

  return meta_rolename.lower()



def check_signable_object_format(signable):
  """
  <Purpose>
    Ensure 'signable' is properly formatted, conformant to
    'SIGNABLE_SCHEMA'.  Return the signing role on
    success.  Note: The 'signed' field of a 'SIGNABLE_SCHEMA' is checked
    against securesystemslib.schema.Any().  The 'signed' field, however, should
    actually hold one of the supported role schemas (e.g., 'ROOT_SCHEMA',
    'TARGETS_SCHEMA').  The role schemas all differ in their format, so this
    function determines exactly which schema is listed in the 'signed' field.

  <Arguments>
    signable:
     The signable object compared against 'SIGNABLE.SCHEMA'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'signable' does not have the
    correct format.

    tuf.exceptions.UnsignedMetadataError, if 'signable' does not have any
    signatures

  <Side Effects>
    None.

  <Returns>
    A string representing the signing role (e.g., 'root', 'targets').
    The role string is returned with characters all lower case.
  """

  # Does 'signable' have the correct type?
  # This check ensures 'signable' conforms to
  # 'SIGNABLE_SCHEMA'.
  SIGNABLE_SCHEMA.check_match(signable)

  try:
    role_type = signable['signed']['_type']

  except (KeyError, TypeError) as error:
    six.raise_from(securesystemslib.exceptions.FormatError(
        'Untyped signable object.'), error)

  try:
    schema = SCHEMAS_BY_TYPE[role_type]

  except KeyError as error:
    six.raise_from(securesystemslib.exceptions.FormatError(
        'Unrecognized type ' + repr(role_type)), error)

  if not signable['signatures']:
    raise tuf.exceptions.UnsignedMetadataError('Signable object of type ' +
        repr(role_type) + ' has no signatures ', signable)

  # 'securesystemslib.exceptions.FormatError' raised if 'signable' does not
  # have a properly formatted role schema.
  schema.check_match(signable['signed'])

  return role_type.lower()



if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running formats.py as a standalone module.
  # python -B formats.py
  import doctest
  doctest.testmod()
