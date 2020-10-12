#!/usr/bin/env python

"""
<Program Name>
  formats.py

<Author>
  Geremy Condra
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  Refactored April 30, 2012. -vladimir.v.diaz

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  A central location for all format-related checking of securesystemslib
  objects. Note: 'formats.py' depends heavily on 'schema.py', so the
  'schema.py' module should be read and understood before tackling this module.

  'formats.py' can be broken down into three sections.  (1) Schemas and object
  matching.  (2) Classes that represent Role Metadata and help produce
  correctly formatted files.  (3) Functions that help produce or verify
  securesystemslib objects.

  The first section deals with schemas and object matching based on format.
  There are two ways of checking the format of objects.  The first method
  raises a 'securesystemslib.exceptions.FormatError' exception if the match
  fails and the other returns a Boolean result.

  securesystemslib.formats.<SCHEMA>.check_match(object)
  securesystemslib.formats.<SCHEMA>.matches(object)

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

  The second section deals with the role metadata classes.  There are
  multiple top-level roles, each with differing metadata formats.
  Example:

  root_object = securesystemslib.formats.RootFile.from_metadata(root_metadata_file)
  targets_metadata = securesystemslib.formats.TargetsFile.make_metadata(...)

  The input and output of these classes are checked against their respective
  schema to ensure correctly formatted metadata.

  The last section contains miscellaneous functions related to the format of
  securesystemslib objects.
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
import re
import string
import datetime
import time
from pip._vendor import six

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import schema as SCHEMA
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions

# Note that in the schema definitions below, the 'SCHEMA.Object' types allow
# additional keys which are not defined. Thus, any additions to them will be
# easily backwards compatible with clients that are already deployed.

ANY_STRING_SCHEMA = SCHEMA.AnyString()
LIST_OF_ANY_STRING_SCHEMA = SCHEMA.ListOf(ANY_STRING_SCHEMA)

# A datetime in 'YYYY-MM-DDTHH:MM:SSZ' ISO 8601 format.  The "Z" zone designator
# for the zero UTC offset is always used (i.e., a numerical offset is not
# supported.)  Example: '2015-10-21T13:20:00Z'.  Note:  This is a simple format
# check, and an ISO8601 string should be fully verified when it is parsed.
ISO8601_DATETIME_SCHEMA = SCHEMA.RegularExpression(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')

# A Unix/POSIX time format.  An integer representing the number of seconds
# since the epoch (January 1, 1970.)  Metadata uses this format for the
# 'expires' field.  Set 'hi' to the upper timestamp limit (year 2038), the max
# value of an int.
UNIX_TIMESTAMP_SCHEMA = SCHEMA.Integer(lo=0, hi=2147483647)

# A hexadecimal value in '23432df87ab..' format.
HEX_SCHEMA = SCHEMA.RegularExpression(r'[a-fA-F0-9]+')

HASH_SCHEMA = HEX_SCHEMA

# A dict in {'sha256': '23432df87ab..', 'sha512': '34324abc34df..', ...} format.
HASHDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = SCHEMA.AnyString(),
  value_schema = HASH_SCHEMA)

# Uniform Resource Locator identifier (e.g., 'https://www.updateframework.com/').
# TODO: Some level of restriction here would be good....  Note that I pulled
#       this from securesystemslib, since it's neither sophisticated nor used
#       by anyone else.
URL_SCHEMA = SCHEMA.AnyString()

# A key identifier (e.g., a hexadecimal value identifying an RSA key).
KEYID_SCHEMA = HASH_SCHEMA

# A list of KEYID_SCHEMA.
KEYIDS_SCHEMA = SCHEMA.ListOf(KEYID_SCHEMA)

# The signing scheme used by a key to generate a signature (e.g.,
# 'rsassa-pss-sha256' is one of the signing schemes for key type 'rsa').
SCHEME_SCHEMA = SCHEMA.AnyString()

# A path string, whether relative or absolute, e.g. 'metadata/root/'
PATH_SCHEMA = SCHEMA.AnyNonemptyString()
PATHS_SCHEMA = SCHEMA.ListOf(PATH_SCHEMA)

# An integer representing logger levels, such as logging.CRITICAL (=50).
# Must be between 0 and 50.
LOGLEVEL_SCHEMA = SCHEMA.Integer(lo=0, hi=50)

# A string representing a named object.
NAME_SCHEMA = SCHEMA.AnyString()
NAMES_SCHEMA = SCHEMA.ListOf(NAME_SCHEMA)

# A byte string representing data.
DATA_SCHEMA = SCHEMA.AnyBytes()

# A text string.  For instance, a string entered by the user.
TEXT_SCHEMA = SCHEMA.AnyString()

# Supported hash algorithms.
HASHALGORITHMS_SCHEMA = SCHEMA.ListOf(SCHEMA.OneOf(
  [SCHEMA.String('md5'), SCHEMA.String('sha1'),
   SCHEMA.String('sha224'), SCHEMA.String('sha256'),
   SCHEMA.String('sha384'), SCHEMA.String('sha512'),
   SCHEMA.String('blake2s'), SCHEMA.String('blake2b'),
   SCHEMA.String('blake2b-256')]))

# The contents of an encrypted key.  Encrypted keys are saved to files
# in this format.
ENCRYPTEDKEY_SCHEMA = SCHEMA.AnyString()

# A value that is either True or False, on or off, etc.
BOOLEAN_SCHEMA = SCHEMA.Boolean()

# The minimum number of bits for an RSA key.  Must be 2048 bits, or greater
# (recommended by TUF).  Recommended RSA key sizes:
# http://www.emc.com/emc-plus/rsa-labs/historical/twirl-and-rsa-key-size.htm#table1
RSAKEYBITS_SCHEMA = SCHEMA.Integer(lo=2048)

# The supported ECDSA signature schemes
ECDSA_SCHEME_SCHEMA = SCHEMA.RegularExpression(r'ecdsa-sha2-nistp(256|384)')

# A pyca-cryptography signature.
PYCACRYPTOSIGNATURE_SCHEMA = SCHEMA.AnyBytes()

# An RSA key in PEM format.
PEMRSA_SCHEMA = SCHEMA.AnyString()

# An ECDSA key in PEM format.
PEMECDSA_SCHEMA = SCHEMA.AnyString()

# A string representing a password.
PASSWORD_SCHEMA = SCHEMA.AnyString()

# A list of passwords.
PASSWORDS_SCHEMA = SCHEMA.ListOf(PASSWORD_SCHEMA)

# The actual values of a key, as opposed to meta data such as a key type and
# key identifier ('rsa', 233df889cb).  For RSA keys, the key value is a pair of
# public and private keys in PEM Format stored as strings.
KEYVAL_SCHEMA = SCHEMA.Object(
  object_name = 'KEYVAL_SCHEMA',
  public = SCHEMA.AnyString(),
  private = SCHEMA.Optional(SCHEMA.AnyString()))

# Public keys CAN have a private portion (for backwards compatibility) which
# MUST be an empty string
PUBLIC_KEYVAL_SCHEMA = SCHEMA.Object(
  object_name = 'KEYVAL_SCHEMA',
  public = SCHEMA.AnyString(),
  private = SCHEMA.Optional(SCHEMA.String("")))

# Supported securesystemslib key types.
KEYTYPE_SCHEMA = SCHEMA.OneOf(
  [SCHEMA.String('rsa'), SCHEMA.String('ed25519'), SCHEMA.String('ecdsa'),
   SCHEMA.RegularExpression(r'ecdsa-sha2-nistp(256|384)')])

# A generic securesystemslib key.  All securesystemslib keys should be saved to
# metadata files in this format.
KEY_SCHEMA = SCHEMA.Object(
  object_name = 'KEY_SCHEMA',
  keytype = SCHEMA.AnyString(),
  scheme = SCHEME_SCHEMA,
  keyval = KEYVAL_SCHEMA,
  expires = SCHEMA.Optional(ISO8601_DATETIME_SCHEMA))

# Like KEY_SCHEMA, but requires keyval's private portion to be unset or empty,
# and optionally includes the supported keyid hash algorithms used to generate
# the key's keyid.
PUBLIC_KEY_SCHEMA = SCHEMA.Object(
  object_name = 'PUBLIC_KEY_SCHEMA',
  keytype = SCHEMA.AnyString(),
  keyid_hash_algorithms = SCHEMA.Optional(HASHALGORITHMS_SCHEMA),
  keyval = PUBLIC_KEYVAL_SCHEMA,
  expires = SCHEMA.Optional(ISO8601_DATETIME_SCHEMA))

# A securesystemslib key object.  This schema simplifies validation of keys
# that may be one of the supported key types.  Supported key types: 'rsa',
# 'ed25519'.
ANYKEY_SCHEMA = SCHEMA.Object(
  object_name = 'ANYKEY_SCHEMA',
  keytype = KEYTYPE_SCHEMA,
  scheme = SCHEME_SCHEMA,
  keyid = KEYID_SCHEMA,
  keyid_hash_algorithms = SCHEMA.Optional(HASHALGORITHMS_SCHEMA),
  keyval = KEYVAL_SCHEMA,
  expires = SCHEMA.Optional(ISO8601_DATETIME_SCHEMA))

# A list of securesystemslib key objects.
ANYKEYLIST_SCHEMA = SCHEMA.ListOf(ANYKEY_SCHEMA)

# RSA signature schemes.
RSA_SCHEME_SCHEMA = SCHEMA.OneOf([
  SCHEMA.RegularExpression(r'rsassa-pss-(md5|sha1|sha224|sha256|sha384|sha512)'),
  SCHEMA.RegularExpression(r'rsa-pkcs1v15-(md5|sha1|sha224|sha256|sha384|sha512)')])

# An RSA securesystemslib key.
RSAKEY_SCHEMA = SCHEMA.Object(
  object_name = 'RSAKEY_SCHEMA',
  keytype = SCHEMA.String('rsa'),
  scheme = RSA_SCHEME_SCHEMA,
  keyid = KEYID_SCHEMA,
  keyid_hash_algorithms = SCHEMA.Optional(HASHALGORITHMS_SCHEMA),
  keyval = KEYVAL_SCHEMA)

# An ECDSA securesystemslib key.
ECDSAKEY_SCHEMA = SCHEMA.Object(
  object_name = 'ECDSAKEY_SCHEMA',
  keytype = SCHEMA.OneOf([SCHEMA.String('ecdsa'),
                          SCHEMA.RegularExpression(r'ecdsa-sha2-nistp(256|384)')]),
  scheme = ECDSA_SCHEME_SCHEMA,
  keyid = KEYID_SCHEMA,
  keyid_hash_algorithms = SCHEMA.Optional(HASHALGORITHMS_SCHEMA),
  keyval = KEYVAL_SCHEMA)

# An ED25519 raw public key, which must be 32 bytes.
ED25519PUBLIC_SCHEMA = SCHEMA.LengthBytes(32)

# An ED25519 raw seed key, which must be 32 bytes.
ED25519SEED_SCHEMA = SCHEMA.LengthBytes(32)

# An ED25519 raw signature, which must be 64 bytes.
ED25519SIGNATURE_SCHEMA = SCHEMA.LengthBytes(64)

# An ECDSA signature.
ECDSASIGNATURE_SCHEMA = SCHEMA.AnyBytes()

# Ed25519 signature schemes.  The vanilla Ed25519 signature scheme is currently
# supported.
ED25519_SIG_SCHEMA = SCHEMA.OneOf([SCHEMA.String('ed25519')])

# An ed25519 key.
ED25519KEY_SCHEMA = SCHEMA.Object(
  object_name = 'ED25519KEY_SCHEMA',
  keytype = SCHEMA.String('ed25519'),
  scheme = ED25519_SIG_SCHEMA,
  keyid = KEYID_SCHEMA,
  keyid_hash_algorithms = SCHEMA.Optional(HASHALGORITHMS_SCHEMA),
  keyval = KEYVAL_SCHEMA)

# GPG key scheme definitions
GPG_HASH_ALGORITHM_STRING = "pgp+SHA2"
GPG_RSA_PUBKEY_METHOD_STRING = "pgp+rsa-pkcsv1.5"
GPG_DSA_PUBKEY_METHOD_STRING = "pgp+dsa-fips-180-2"
GPG_ED25519_PUBKEY_METHOD_STRING = "pgp+eddsa-ed25519"

def _create_gpg_pubkey_with_subkey_schema(pubkey_schema):
  """Helper method to extend the passed public key schema with an optional
  dictionary of sub public keys "subkeys" with the same schema."""
  schema = pubkey_schema
  subkey_schema_tuple =  ("subkeys", SCHEMA.Optional(
        SCHEMA.DictOf(
          key_schema=KEYID_SCHEMA,
          value_schema=pubkey_schema
          )
        )
      )
  # Any subclass of `securesystemslib.schema.Object` stores the schemas that
  # define the attributes of the object in its `_required` property, even if
  # such a schema is of type `Optional`.
  # TODO: Find a way that does not require to access a protected member
  schema._required.append(subkey_schema_tuple) # pylint: disable=protected-access
  return schema

GPG_RSA_PUBKEYVAL_SCHEMA = SCHEMA.Object(
  object_name = "GPG_RSA_PUBKEYVAL_SCHEMA",
  e = SCHEMA.AnyString(),
  n = HEX_SCHEMA
)

# We have to define GPG_RSA_PUBKEY_SCHEMA in two steps, because it is
# self-referential. Here we define a shallow _GPG_RSA_PUBKEY_SCHEMA, which we
# use below to create the self-referential GPG_RSA_PUBKEY_SCHEMA.
_GPG_RSA_PUBKEY_SCHEMA = SCHEMA.Object(
  object_name = "GPG_RSA_PUBKEY_SCHEMA",
  type = SCHEMA.String("rsa"),
  method = SCHEMA.String(GPG_RSA_PUBKEY_METHOD_STRING),
  hashes = SCHEMA.ListOf(SCHEMA.String(GPG_HASH_ALGORITHM_STRING)),
  creation_time = SCHEMA.Optional(UNIX_TIMESTAMP_SCHEMA),
  validity_period = SCHEMA.Optional(SCHEMA.Integer(lo=0)),
  keyid = KEYID_SCHEMA,
  keyval = SCHEMA.Object(
      public = GPG_RSA_PUBKEYVAL_SCHEMA,
      private = SCHEMA.String("")
    )
)
GPG_RSA_PUBKEY_SCHEMA = _create_gpg_pubkey_with_subkey_schema(
    _GPG_RSA_PUBKEY_SCHEMA)

GPG_DSA_PUBKEYVAL_SCHEMA = SCHEMA.Object(
  object_name = "GPG_DSA_PUBKEYVAL_SCHEMA",
  y = HEX_SCHEMA,
  p = HEX_SCHEMA,
  q = HEX_SCHEMA,
  g = HEX_SCHEMA
)

# C.f. comment above _GPG_RSA_PUBKEY_SCHEMA definition
_GPG_DSA_PUBKEY_SCHEMA = SCHEMA.Object(
  object_name = "GPG_DSA_PUBKEY_SCHEMA",
  type = SCHEMA.String("dsa"),
  method = SCHEMA.String(GPG_DSA_PUBKEY_METHOD_STRING),
  hashes = SCHEMA.ListOf(SCHEMA.String(GPG_HASH_ALGORITHM_STRING)),
  creation_time = SCHEMA.Optional(UNIX_TIMESTAMP_SCHEMA),
  validity_period = SCHEMA.Optional(SCHEMA.Integer(lo=0)),
  keyid = KEYID_SCHEMA,
  keyval = SCHEMA.Object(
      public = GPG_DSA_PUBKEYVAL_SCHEMA,
      private = SCHEMA.String("")
    )
)

GPG_DSA_PUBKEY_SCHEMA = _create_gpg_pubkey_with_subkey_schema(
    _GPG_DSA_PUBKEY_SCHEMA)

GPG_ED25519_PUBKEYVAL_SCHEMA = SCHEMA.Object(
  object_name = "GPG_ED25519_PUBKEYVAL_SCHEMA",
  q = HEX_SCHEMA,
)

# C.f. comment above _GPG_RSA_PUBKEY_SCHEMA definition
_GPG_ED25519_PUBKEY_SCHEMA = SCHEMA.Object(
  object_name = "GPG_ED25519_PUBKEY_SCHEMA",
  type = SCHEMA.String("eddsa"),
  method = SCHEMA.String(GPG_ED25519_PUBKEY_METHOD_STRING),
  hashes = SCHEMA.ListOf(SCHEMA.String(GPG_HASH_ALGORITHM_STRING)),
  creation_time = SCHEMA.Optional(UNIX_TIMESTAMP_SCHEMA),
  validity_period = SCHEMA.Optional(SCHEMA.Integer(lo=0)),
  keyid = KEYID_SCHEMA,
  keyval = SCHEMA.Object(
      public = GPG_ED25519_PUBKEYVAL_SCHEMA,
      private = SCHEMA.String("")
    )
)
GPG_ED25519_PUBKEY_SCHEMA = _create_gpg_pubkey_with_subkey_schema(
    _GPG_ED25519_PUBKEY_SCHEMA)

GPG_PUBKEY_SCHEMA = SCHEMA.OneOf([GPG_RSA_PUBKEY_SCHEMA,
    GPG_DSA_PUBKEY_SCHEMA, GPG_ED25519_PUBKEY_SCHEMA])

GPG_SIGNATURE_SCHEMA = SCHEMA.Object(
    object_name = "SIGNATURE_SCHEMA",
    keyid = KEYID_SCHEMA,
    short_keyid = SCHEMA.Optional(KEYID_SCHEMA),
    other_headers = HEX_SCHEMA,
    signature = HEX_SCHEMA,
    info = SCHEMA.Optional(SCHEMA.Any()),
  )

# A single signature of an object.  Indicates the signature, and the KEYID of
# the signing key.  I debated making the signature schema not contain the key
# ID and instead have the signatures of a file be a dictionary with the key
# being the keyid and the value being the signature schema without the keyid.
# That would be under the argument that a key should only be able to sign a
# file once.
SIGNATURE_SCHEMA = SCHEMA.Object(
  object_name = 'SIGNATURE_SCHEMA',
  keyid = KEYID_SCHEMA,
  sig = HEX_SCHEMA)

# A dict where the dict keys hold a keyid and the dict values a key object.
KEYDICT_SCHEMA = SCHEMA.DictOf(
  key_schema = KEYID_SCHEMA,
  value_schema = KEY_SCHEMA)

ANY_SIGNATURE_SCHEMA = SCHEMA.OneOf([SIGNATURE_SCHEMA,
    GPG_SIGNATURE_SCHEMA])

# List of ANY_SIGNATURE_SCHEMA.
SIGNATURES_SCHEMA = SCHEMA.ListOf(ANY_SIGNATURE_SCHEMA)

# A signable object.  Holds the signing role and its associated signatures.
SIGNABLE_SCHEMA = SCHEMA.Object(
  object_name = 'SIGNABLE_SCHEMA',
  signed = SCHEMA.Any(),
  signatures = SIGNATURES_SCHEMA)

# Note: Verification keys can have private portions but in case of GPG we
# only have a PUBKEY_SCHEMA (because we never export private gpg keys from
# the gpg keyring)
ANY_VERIFICATION_KEY_SCHEMA = SCHEMA.OneOf([ANYKEY_SCHEMA,
    GPG_PUBKEY_SCHEMA])

VERIFICATION_KEY_DICT_SCHEMA = SCHEMA.DictOf(
  key_schema = KEYID_SCHEMA,
  value_schema = ANY_VERIFICATION_KEY_SCHEMA)

ANY_KEYDICT_SCHEMA = SCHEMA.OneOf([KEYDICT_SCHEMA,
    VERIFICATION_KEY_DICT_SCHEMA])

ANY_PUBKEY_SCHEMA = SCHEMA.OneOf([PUBLIC_KEY_SCHEMA, GPG_PUBKEY_SCHEMA])

ANY_PUBKEY_DICT_SCHEMA = SCHEMA.DictOf(
  key_schema = KEYID_SCHEMA,
  value_schema = ANY_PUBKEY_SCHEMA)





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




def _canonical_string_encoder(string):
  """
  <Purpose>
    Encode 'string' to canonical string format.

  <Arguments>
    string:
      The string to encode.

  <Exceptions>
    None.

  <Side Effects>
    None.

  <Returns>
    A string with the canonical-encoded 'string' embedded.
  """

  string = '"%s"' % re.sub(r'(["\\])', r'\\\1', string)

  return string


def _encode_canonical(object, output_function):
  # Helper for encode_canonical.  Older versions of json.encoder don't
  # even let us replace the separators.

  if isinstance(object, six.string_types):
    output_function(_canonical_string_encoder(object))
  elif object is True:
    output_function("true")
  elif object is False:
    output_function("false")
  elif object is None:
    output_function("null")
  elif isinstance(object, six.integer_types):
    output_function(str(object))
  elif isinstance(object, (tuple, list)):
    output_function("[")
    if len(object):
      for item in object[:-1]:
        _encode_canonical(item, output_function)
        output_function(",")
      _encode_canonical(object[-1], output_function)
    output_function("]")
  elif isinstance(object, dict):
    output_function("{")
    if len(object):
      items = sorted(six.iteritems(object))
      for key, value in items[:-1]:
        output_function(_canonical_string_encoder(key))
        output_function(":")
        _encode_canonical(value, output_function)
        output_function(",")
      key, value = items[-1]
      output_function(_canonical_string_encoder(key))
      output_function(":")
      _encode_canonical(value, output_function)
    output_function("}")
  else:
    raise securesystemslib.exceptions.FormatError('I cannot encode '+repr(object))


def encode_canonical(object, output_function=None):
  """
  <Purpose>
    Encode 'object' in canonical JSON form, as specified at
    http://wiki.laptop.org/go/Canonical_JSON .  It's a restricted
    dialect of JSON in which keys are always lexically sorted,
    there is no whitespace, floats aren't allowed, and only quote
    and backslash get escaped.  The result is encoded in UTF-8,
    and the resulting bits are passed to output_function (if provided),
    or joined into a string and returned.

    Note: This function should be called prior to computing the hash or
    signature of a JSON object in securesystemslib.  For example, generating a
    signature of a signing role object such as 'ROOT_SCHEMA' is required to
    ensure repeatable hashes are generated across different json module
    versions and platforms.  Code elsewhere is free to dump JSON objects in any
    format they wish (e.g., utilizing indentation and single quotes around
    object keys).  These objects are only required to be in "canonical JSON"
    format when their hashes or signatures are needed.

    >>> encode_canonical("")
    '""'
    >>> encode_canonical([1, 2, 3])
    '[1,2,3]'
    >>> encode_canonical([])
    '[]'
    >>> encode_canonical({"A": [99]})
    '{"A":[99]}'
    >>> encode_canonical({"x" : 3, "y" : 2})
    '{"x":3,"y":2}'

  <Arguments>
    object:
      The object to be encoded.

    output_function:
      The result will be passed as arguments to 'output_function'
      (e.g., output_function('result')).

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'object' cannot be encoded or
    'output_function' is not callable.

  <Side Effects>
    The results are fed to 'output_function()' if 'output_function' is set.

  <Returns>
    A string representing the 'object' encoded in canonical JSON form.
  """

  result = None
  # If 'output_function' is unset, treat it as
  # appending to a list.
  if output_function is None:
    result = []
    output_function = result.append

  try:
    _encode_canonical(object, output_function)

  except (TypeError, securesystemslib.exceptions.FormatError) as e:
    message = 'Could not encode ' + repr(object) + ': ' + str(e)
    raise securesystemslib.exceptions.FormatError(message)

  # Return the encoded 'object' as a string.
  # Note: Implies 'output_function' is None,
  # otherwise results are sent to 'output_function'.
  if result is not None:
    return ''.join(result)
