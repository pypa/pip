#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  sig.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  February 28, 2012.   Based on a previous version by Geremy Condra.

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  Survivable key compromise is one feature of a secure update system
  incorporated into TUF's design. Responsibility separation through
  the use of multiple roles, multi-signature trust, and explicit and
  implicit key revocation are some of the mechanisms employed towards
  this goal of survivability.  These mechanisms can all be seen in
  play by the functions available in this module.

  The signed metadata files utilized by TUF to download target files
  securely are used and represented here as the 'signable' object.
  More precisely, the signature structures contained within these metadata
  files are packaged into 'signable' dictionaries.  This module makes it
  possible to capture the states of these signatures by organizing the
  keys into different categories.  As keys are added and removed, the
  system must securely and efficiently verify the status of these signatures.
  For instance, a bunch of keys have recently expired. How many valid keys
  are now available to the Snapshot role?  This question can be answered by
  get_signature_status(), which will return a full 'status report' of these
  'signable' dicts.  This module also provides a convenient verify() function
  that will determine if a role still has a sufficient number of valid keys.
  If a caller needs to update the signatures of a 'signable' object, there
  is also a function for that.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

from pip._vendor import tuf
class _Dummy(object):
  pass
tuf = _Dummy()
from pip._vendor.tuf import exceptions as _tuf_exceptions
tuf.exceptions = _tuf_exceptions
from pip._vendor.tuf import keydb as _tuf_keydb
tuf.keydb = _tuf_keydb
from pip._vendor.tuf import roledb as _tuf_roledb
tuf.roledb = _tuf_roledb
from pip._vendor.tuf import formats as _tuf_formats
tuf.formats = _tuf_formats

from pip._vendor import securesystemslib
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import keys as _securesystemslib_keys
securesystemslib.keys = _securesystemslib_keys

# See 'log.py' to learn how logging is handled in TUF.
logger = logging.getLogger(__name__)

def get_signature_status(signable, role=None, repository_name='default',
    threshold=None, keyids=None):
  """
  <Purpose>
    Return a dictionary representing the status of the signatures listed in
    'signable'. Signatures in the returned dictionary are identified by the
    signature keyid and can have a status of either:

    * bad -- Invalid signature
    * good -- Valid signature from key that is available in 'tuf.keydb', and is
      authorized for the passed role as per 'tuf.roledb' (authorization may be
      overwritten by passed 'keyids').
    * unknown -- Signature from key that is not available in 'tuf.keydb', or if
      'role' is None.
    * unknown signing schemes -- Signature from key with unknown signing
      scheme.
    * untrusted -- Valid signature from key that is available in 'tuf.keydb',
      but is not trusted for the passed role as per 'tuf.roledb' or the passed
      'keyids'.

    NOTE: The result may contain duplicate keyids or keyids that reference the
    same key, if 'signable' lists multiple signatures from the same key.

  <Arguments>
    signable:
      A dictionary containing a list of signatures and a 'signed' identifier.
      signable = {'signed': 'signer',
                  'signatures': [{'keyid': keyid,
                                  'sig': sig}]}

      Conformant to tuf.formats.SIGNABLE_SCHEMA.

    role:
      TUF role string (e.g. 'root', 'targets', 'snapshot' or timestamp).

    threshold:
      Rather than reference the role's threshold as set in tuf.roledb.py, use
      the given 'threshold' to calculate the signature status of 'signable'.
      'threshold' is an integer value that sets the role's threshold value, or
      the minimum number of signatures needed for metadata to be considered
      fully signed.

    keyids:
      Similar to the 'threshold' argument, use the supplied list of 'keyids'
      to calculate the signature status, instead of referencing the keyids
      in tuf.roledb.py for 'role'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'signable' does not have the
    correct format.

    tuf.exceptions.UnknownRoleError, if 'role' is not recognized.

  <Side Effects>
    None.

  <Returns>
    A dictionary representing the status of the signatures in 'signable'.
    Conformant to tuf.formats.SIGNATURESTATUS_SCHEMA.
  """

  # Do the arguments have the correct format?  This check will ensure that
  # arguments have the appropriate number of objects and object types, and that
  # all dict keys are properly named.  Raise
  # 'securesystemslib.exceptions.FormatError' if the check fails.
  tuf.formats.SIGNABLE_SCHEMA.check_match(signable)
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  if role is not None:
    tuf.formats.ROLENAME_SCHEMA.check_match(role)

  if threshold is not None:
    tuf.formats.THRESHOLD_SCHEMA.check_match(threshold)

  if keyids is not None:
    securesystemslib.formats.KEYIDS_SCHEMA.check_match(keyids)

  # The signature status dictionary returned.
  signature_status = {}
  good_sigs = []
  bad_sigs = []
  unknown_sigs = []
  untrusted_sigs = []
  unknown_signing_schemes = []

  # Extract the relevant fields from 'signable' that will allow us to identify
  # the different classes of keys (i.e., good_sigs, bad_sigs, etc.).
  signed = securesystemslib.formats.encode_canonical(signable['signed']).encode('utf-8')
  signatures = signable['signatures']

  # Iterate the signatures and enumerate the signature_status fields.
  # (i.e., good_sigs, bad_sigs, etc.).
  for signature in signatures:
    keyid = signature['keyid']

    # Does the signature use an unrecognized key?
    try:
      key = tuf.keydb.get_key(keyid, repository_name)

    except tuf.exceptions.UnknownKeyError:
      unknown_sigs.append(keyid)
      continue

    # Does the signature use an unknown/unsupported signing scheme?
    try:
      valid_sig = securesystemslib.keys.verify_signature(key, signature, signed)

    except securesystemslib.exceptions.UnsupportedAlgorithmError:
      unknown_signing_schemes.append(keyid)
      continue

    # We are now dealing with either a trusted or untrusted key...
    if valid_sig:
      if role is not None:

        # Is this an unauthorized key? (a keyid associated with 'role')
        # Note that if the role is not known, tuf.exceptions.UnknownRoleError
        # is raised here.
        if keyids is None:
          keyids = tuf.roledb.get_role_keyids(role, repository_name)

        if keyid not in keyids:
          untrusted_sigs.append(keyid)
          continue

      # This is an unset role, thus an unknown signature.
      else:
        unknown_sigs.append(keyid)
        continue

      # Identify good/authorized key.
      good_sigs.append(keyid)

    else:
      # This is a bad signature for a trusted key.
      bad_sigs.append(keyid)

  # Retrieve the threshold value for 'role'.  Raise
  # tuf.exceptions.UnknownRoleError if we were given an invalid role.
  if role is not None:
    if threshold is None:
      # Note that if the role is not known, tuf.exceptions.UnknownRoleError is
      # raised here.
      threshold = tuf.roledb.get_role_threshold(
          role, repository_name=repository_name)

    else:
      logger.debug('Not using roledb.py\'s threshold for ' + repr(role))

  else:
    threshold = 0

  # Build the signature_status dict.
  signature_status['threshold'] = threshold
  signature_status['good_sigs'] = good_sigs
  signature_status['bad_sigs'] = bad_sigs
  signature_status['unknown_sigs'] = unknown_sigs
  signature_status['untrusted_sigs'] = untrusted_sigs
  signature_status['unknown_signing_schemes'] = unknown_signing_schemes

  return signature_status





def verify(signable, role, repository_name='default', threshold=None,
    keyids=None):
  """
  <Purpose>
    Verify that 'signable' has a valid threshold of authorized signatures
    identified by unique keyids. The threshold and whether a keyid is
    authorized is determined by querying the 'threshold' and 'keyids' info for
    the passed 'role' in 'tuf.roledb'. Both values can be overwritten by
    passing the 'threshold' or 'keyids' arguments.

    NOTE:
    - Signatures with identical authorized keyids only count towards the
      threshold once.
    - Signatures with the same key only count toward the threshold once.

  <Arguments>
    signable:
      A dictionary containing a list of signatures and a 'signed' identifier
      that conforms to SIGNABLE_SCHEMA, e.g.:
      signable = {'signed':, 'signatures': [{'keyid':, 'method':, 'sig':}]}

    role:
      TUF role string (e.g. 'root', 'targets', 'snapshot' or timestamp).

    threshold:
      Rather than reference the role's threshold as set in tuf.roledb.py, use
      the given 'threshold' to calculate the signature status of 'signable'.
      'threshold' is an integer value that sets the role's threshold value, or
      the minimum number of signatures needed for metadata to be considered
      fully signed.

    keyids:
      Similar to the 'threshold' argument, use the supplied list of 'keyids'
      to calculate the signature status, instead of referencing the keyids
      in tuf.roledb.py for 'role'.

  <Exceptions>
    tuf.exceptions.UnknownRoleError, if 'role' is not recognized.

    securesystemslib.exceptions.FormatError, if 'signable' is not formatted
    correctly.

    securesystemslib.exceptions.Error, if an invalid threshold is encountered.

  <Side Effects>
    tuf.sig.get_signature_status() called.  Any exceptions thrown by
    get_signature_status() will be caught here and re-raised.

  <Returns>
    Boolean.  True if the number of good unique (by keyid) signatures >= the
    role's threshold, False otherwise.
  """

  tuf.formats.SIGNABLE_SCHEMA.check_match(signable)
  tuf.formats.ROLENAME_SCHEMA.check_match(role)
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Retrieve the signature status.  tuf.sig.get_signature_status() raises:
  # tuf.exceptions.UnknownRoleError
  # securesystemslib.exceptions.FormatError.  'threshold' and 'keyids' are also
  # validated.
  status = get_signature_status(signable, role, repository_name, threshold, keyids)

  # Retrieve the role's threshold and the authorized keys of 'status'
  threshold = status['threshold']
  good_sigs = status['good_sigs']

  # Does 'status' have the required threshold of signatures?
  # First check for invalid threshold values before returning result.
  # Note: get_signature_status() is expected to verify that 'threshold' is
  # not None or <= 0.
  if threshold is None or threshold <= 0: #pragma: no cover
    raise securesystemslib.exceptions.Error("Invalid threshold: " + repr(threshold))

  unique_keys = set()
  for keyid in good_sigs:
    key = tuf.keydb.get_key(keyid, repository_name)
    unique_keys.add(key['keyval']['public'])

  return len(unique_keys) >= threshold





def may_need_new_keys(signature_status):
  """
  <Purpose>
    Return true iff downloading a new set of keys might tip this
    signature status over to valid.  This is determined by checking
    if either the number of unknown or untrusted keys is > 0.

  <Arguments>
    signature_status:
      The dictionary returned by tuf.sig.get_signature_status().

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'signature_status does not have
    the correct format.

  <Side Effects>
    None.

  <Returns>
    Boolean.
  """

  # Does 'signature_status' have the correct format?
  # This check will ensure 'signature_status' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  tuf.formats.SIGNATURESTATUS_SCHEMA.check_match(signature_status)

  unknown = signature_status['unknown_sigs']
  untrusted = signature_status['untrusted_sigs']

  return len(unknown) or len(untrusted)





def generate_rsa_signature(signed, rsakey_dict):
  """
  <Purpose>
    Generate a new signature dict presumably to be added to the 'signatures'
    field of 'signable'.  The 'signable' dict is of the form:

    {'signed': 'signer',
               'signatures': [{'keyid': keyid,
                               'method': 'evp',
                               'sig': sig}]}

    The 'signed' argument is needed here for the signing process.
    The 'rsakey_dict' argument is used to generate 'keyid', 'method', and 'sig'.

    The caller should ensure the returned signature is not already in
    'signable'.

  <Arguments>
    signed:
      The data used by 'securesystemslib.keys.create_signature()' to generate
      signatures.  It is stored in the 'signed' field of 'signable'.

    rsakey_dict:
      The RSA key, a 'securesystemslib.formats.RSAKEY_SCHEMA' dictionary.
      Used here to produce 'keyid', 'method', and 'sig'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'rsakey_dict' does not have the
    correct format.

    TypeError, if a private key is not defined for 'rsakey_dict'.

  <Side Effects>
    None.

  <Returns>
    Signature dictionary conformant to securesystemslib.formats.SIGNATURE_SCHEMA.
    Has the form:
    {'keyid': keyid, 'method': 'evp', 'sig': sig}
  """

  # We need 'signed' in canonical JSON format to generate
  # the 'method' and 'sig' fields of the signature.
  signed = securesystemslib.formats.encode_canonical(signed).encode('utf-8')

  # Generate the RSA signature.
  # Raises securesystemslib.exceptions.FormatError and TypeError.
  signature = securesystemslib.keys.create_signature(rsakey_dict, signed)

  return signature
