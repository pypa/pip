#!/usr/bin/env python

"""
<Program Name>
  interface.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  January 5, 2017.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Provide an interface to the cryptography functions available in
  securesystemslib.  The interface can be used with the Python interpreter in
  interactive mode, or imported directly into a Python module.  See
  'securesystemslib/README' for the complete guide to using 'interface.py'.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import errno
import sys
import time
import datetime
import getpass
import logging
import tempfile
import shutil
import json
import gzip
import random

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import settings as _securesystemslib_settings
securesystemslib.settings = _securesystemslib_settings
from pip._vendor.securesystemslib import storage as _securesystemslib_storage
securesystemslib.storage = _securesystemslib_storage
from pip._vendor.securesystemslib import util as _securesystemslib_util
securesystemslib.util = _securesystemslib_util
from pip._vendor.securesystemslib import keys as _securesystemslib_keys
securesystemslib.keys = _securesystemslib_keys

from pip._vendor.securesystemslib import KEY_TYPE_RSA, KEY_TYPE_ED25519, KEY_TYPE_ECDSA

from pip._vendor import six

logger = logging.getLogger(__name__)

try:
  from pip._vendor.colorama import Fore
  TERM_RED = Fore.RED
  TERM_RESET = Fore.RESET
except ImportError: # pragma: no cover
  logger.debug("Failed to find colorama module, terminal output won't be colored")
  TERM_RED = ''
  TERM_RESET = ''

# Recommended RSA key sizes:
# https://en.wikipedia.org/wiki/Key_size#Asymmetric_algorithm_key_lengths
# Based on the above, RSA keys of size 3072 bits are expected to provide
# security through 2031 and beyond.
DEFAULT_RSA_KEY_BITS = 3072





def get_password(prompt='Password: ', confirm=False):
  """
  <Purpose>
    Return the password entered by the user.  If 'confirm' is True, the user is
    asked to enter the previously entered password once again.  If they match,
    the password is returned to the caller.

  <Arguments>
    prompt:
      The text of the password prompt that is displayed to the user.

    confirm:
      Boolean indicating whether the user should be prompted for the password
      a second time.  The two entered password must match, otherwise the
      user is again prompted for a password.

  <Exceptions>
    None.

  <Side Effects>
    None.

  <Returns>
    The password entered by the user.
  """

  # Are the arguments the expected type?
  # If not, raise 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.TEXT_SCHEMA.check_match(prompt)
  securesystemslib.formats.BOOLEAN_SCHEMA.check_match(confirm)

  while True:
    # getpass() prompts the user for a password without echoing
    # the user input.
    password = getpass.getpass(prompt, sys.stderr)

    if not confirm:
      return password
    password2 = getpass.getpass('Confirm: ', sys.stderr)

    if password == password2:
      return password

    else:
      print('Mismatch; try again.')





def generate_and_write_rsa_keypair(filepath=None, bits=DEFAULT_RSA_KEY_BITS,
    password=None):
  """
  <Purpose>
    Generate an RSA key pair.  The public portion of the generated RSA key is
    saved to <'filepath'>.pub, whereas the private key portion is saved to
    <'filepath'>.  If no password is given, the user is prompted for one.  If
    the 'password' is an empty string, the private key is saved unencrypted to
    <'filepath'>.  If the filepath is not given, the KEYID is used as the
    filename and the keypair saved to the current working directory.

    The best available form of encryption, for a given key's backend, is used
    with pyca/cryptography.  According to their documentation, "it is a curated
    encryption choice and the algorithm may change over time."

  <Arguments>
    filepath:
      The public and private key files are saved to <filepath>.pub and
      <filepath>, respectively.  If the filepath is not given, the public and
      private keys are saved to the current working directory as <KEYID>.pub
      and <KEYID>.  KEYID is the generated key's KEYID.

    bits:
      The number of bits of the generated RSA key.

    password:
      The password to encrypt 'filepath'.  If None, the user is prompted for a
      password.  If an empty string is given, the private key is written to
      disk unencrypted.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

  <Side Effects>
    Writes key files to '<filepath>' and '<filepath>.pub'.

  <Returns>
    The 'filepath' of the written key.
  """

  # Does 'bits' have the correct format?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.RSAKEYBITS_SCHEMA.check_match(bits)

  # Generate the public and private RSA keys.
  rsa_key = securesystemslib.keys.generate_rsa_key(bits)
  public = rsa_key['keyval']['public']
  private = rsa_key['keyval']['private']

  if not filepath:
    filepath = os.path.join(os.getcwd(), rsa_key['keyid'])

  else:
    logger.debug('The filepath has been specified.  Not using the key\'s'
        ' KEYID as the default filepath.')

  # Does 'filepath' have the correct format?
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # If the caller does not provide a password argument, prompt for one.
  if password is None:

    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    password = get_password('Enter a password for the encrypted RSA'
        ' key (' + TERM_RED + filepath + TERM_RESET + '): ',
        confirm=True)

  else:
    logger.debug('The password has been specified.  Not prompting for one')

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  # Encrypt the private key if 'password' is set.
  if len(password):
    private = securesystemslib.keys.create_rsa_encrypted_pem(private, password)

  else:
    logger.debug('An empty password was given.  Not encrypting the private key.')

  # If the parent directory of filepath does not exist,
  # create it (and all its parent directories, if necessary).
  securesystemslib.util.ensure_parent_dir(filepath)

  # Write the public key (i.e., 'public', which is in PEM format) to
  # '<filepath>.pub'.  (1) Create a temporary file, (2) write the contents of
  # the public key, and (3) move to final destination.
  file_object = tempfile.TemporaryFile()
  file_object.write(public.encode('utf-8'))
  # The temporary file is closed after the final move.
  securesystemslib.util.persist_temp_file(file_object, filepath + '.pub')

  # Write the private key in encrypted PEM format to '<filepath>'.
  # Unlike the public key file, the private key does not have a file
  # extension.
  file_object = tempfile.TemporaryFile()
  file_object.write(private.encode('utf-8'))
  securesystemslib.util.persist_temp_file(file_object, filepath)

  return filepath




def import_rsa_privatekey_from_file(filepath, password=None,
    scheme='rsassa-pss-sha256', prompt=False,
    storage_backend=None):
  """
  <Purpose>
    Import the PEM file in 'filepath' containing the private key.

    If password is passed use passed password for decryption.
    If prompt is True use entered password for decryption.
    If no password is passed and either prompt is False or if the password
    entered at the prompt is an empty string, omit decryption, treating the
    key as if it is not encrypted.
    If password is passed and prompt is True, an error is raised. (See below.)

    The returned key is an object in the
    'securesystemslib.formats.RSAKEY_SCHEMA' format.

  <Arguments>
    filepath:
      <filepath> file, an RSA encrypted PEM file.  Unlike the public RSA PEM
      key file, 'filepath' does not have an extension.

    password:
      The passphrase to decrypt 'filepath'.

    scheme:
      The signature scheme used by the imported key.

    prompt:
      If True the user is prompted for a passphrase to decrypt 'filepath'.
      Default is False.

    storage_backend:
      An object which implements
      securesystemslib.storage.StorageBackendInterface. When no object is
      passed a FilesystemBackend will be instantiated and used.

  <Exceptions>
    ValueError, if 'password' is passed and 'prompt' is True.

    ValueError, if 'password' is passed and it is an empty string.

    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.FormatError, if the entered password is
    improperly formatted.

    IOError, if 'filepath' can't be loaded.

    securesystemslib.exceptions.CryptoError, if a password is available
    and 'filepath' is not a valid key file encrypted using that password.

    securesystemslib.exceptions.CryptoError, if no password is available
    and 'filepath' is not a valid non-encrypted key file.

  <Side Effects>
    The contents of 'filepath' are read, optionally decrypted, and returned.

  <Returns>
    An RSA key object, conformant to 'securesystemslib.formats.RSAKEY_SCHEMA'.

  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # Is 'scheme' properly formatted?
  securesystemslib.formats.RSA_SCHEME_SCHEMA.check_match(scheme)

  if password and prompt:
    raise ValueError("Passing 'password' and 'prompt' True is not allowed.")

  # If 'password' was passed check format and that it is not empty.
  if password is not None:
    securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

    # TODO: PASSWORD_SCHEMA should be securesystemslib.schema.AnyString(min=1)
    if not len(password):
      raise ValueError('Password must be 1 or more characters')

  elif prompt:
    # Password confirmation disabled here, which should ideally happen only
    # when creating encrypted key files (i.e., improve usability).
    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    # NOTE: A user who gets prompted for a password, can only signal that the
    # key is not encrypted by entering no password in the prompt, as opposed
    # to a programmer who can call the function with or without a 'password'.
    # Hence, we treat an empty password here, as if no 'password' was passed.
    password = get_password('Enter a password for an encrypted RSA'
        ' file \'' + TERM_RED + filepath + TERM_RESET + '\': ',
        confirm=False) or None

  if password is not None:
    # This check will not fail, because a mal-formatted passed password fails
    # above and an entered password will always be a string (see get_password)
    # However, we include it in case PASSWORD_SCHEMA or get_password changes.
    securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  else:
    logger.debug('No password was given. Attempting to import an'
        ' unencrypted file.')

  if storage_backend is None:
    storage_backend = securesystemslib.storage.FilesystemBackend()

  # Read the contents of 'filepath' that should be a PEM formatted private key.
  with storage_backend.get(filepath) as file_object:
    pem_key = file_object.read().decode('utf-8')

  # Convert 'pem_key' to 'securesystemslib.formats.RSAKEY_SCHEMA' format.
  # Raise 'securesystemslib.exceptions.CryptoError' if 'pem_key' is invalid.
  # If 'password' is None decryption will be omitted.
  rsa_key = securesystemslib.keys.import_rsakey_from_private_pem(pem_key,
      scheme, password)

  return rsa_key





def import_rsa_publickey_from_file(filepath, scheme='rsassa-pss-sha256',
    storage_backend=None):
  """
  <Purpose>
    Import the RSA key stored in 'filepath'.  The key object returned is in the
    format 'securesystemslib.formats.RSAKEY_SCHEMA'.  If the RSA PEM in
    'filepath' contains a private key, it is discarded.

  <Arguments>
    filepath:
      <filepath>.pub file, an RSA PEM file.

    scheme:
      The signature scheme used by the imported key.

    storage_backend:
      An object which implements
      securesystemslib.storage.StorageBackendInterface. When no object is
      passed a FilesystemBackend will be instantiated and used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'filepath' is improperly
    formatted.

    securesystemslib.exceptions.Error, if a valid RSA key object cannot be
    generated.  This may be caused by an improperly formatted PEM file.

  <Side Effects>
    'filepath' is read and its contents extracted.

  <Returns>
    An RSA key object conformant to 'securesystemslib.formats.RSAKEY_SCHEMA'.
  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # Is 'scheme' properly formatted?
  securesystemslib.formats.RSA_SCHEME_SCHEMA.check_match(scheme)

  if storage_backend is None:
    storage_backend = securesystemslib.storage.FilesystemBackend()

  # Read the contents of the key file that should be in PEM format and contains
  # the public portion of the RSA key.
  with storage_backend.get(filepath) as file_object:
    rsa_pubkey_pem = file_object.read().decode('utf-8')

  # Convert 'rsa_pubkey_pem' to 'securesystemslib.formats.RSAKEY_SCHEMA' format.
  try:
    rsakey_dict = securesystemslib.keys.import_rsakey_from_public_pem(
        rsa_pubkey_pem, scheme)

  except securesystemslib.exceptions.FormatError as e:
    raise securesystemslib.exceptions.Error('Cannot import improperly formatted'
      ' PEM file.' + repr(str(e)))

  return rsakey_dict





def generate_and_write_ed25519_keypair(filepath=None, password=None):
  """
  <Purpose>
    Generate an Ed25519 keypair, where the encrypted key (using 'password' as
    the passphrase) is saved to <'filepath'>.  The public key portion of the
    generated Ed25519 key is saved to <'filepath'>.pub.  If the filepath is not
    given, the KEYID is used as the filename and the keypair saved to the
    current working directory.

    The private key is encrypted according to 'cryptography's approach:
    "Encrypt using the best available encryption for a given key's backend.
    This is a curated encryption choice and the algorithm may change over
    time."

  <Arguments>
    filepath:
      The public and private key files are saved to <filepath>.pub and
      <filepath>, respectively.  If the filepath is not given, the public and
      private keys are saved to the current working directory as <KEYID>.pub
      and <KEYID>.  KEYID is the generated key's KEYID.

    password:
      The password, or passphrase, to encrypt the private portion of the
      generated Ed25519 key.  A symmetric encryption key is derived from
      'password', so it is not directly used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if 'filepath' cannot be encrypted.

  <Side Effects>
    Writes key files to '<filepath>' and '<filepath>.pub'.

  <Returns>
    The 'filepath' of the written key.
  """

  # Generate a new Ed25519 key object.
  ed25519_key = securesystemslib.keys.generate_ed25519_key()

  if not filepath:
    filepath = os.path.join(os.getcwd(), ed25519_key['keyid'])

  else:
    logger.debug('The filepath has been specified.  Not using the key\'s'
        ' KEYID as the default filepath.')

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # If the caller does not provide a password argument, prompt for one.
  if password is None:

    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    password = get_password('Enter a password for the Ed25519'
        ' key (' + TERM_RED + filepath + TERM_RESET + '): ',
        confirm=True)

  else:
    logger.debug('The password has been specified. Not prompting for one.')

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  # If the parent directory of filepath does not exist,
  # create it (and all its parent directories, if necessary).
  securesystemslib.util.ensure_parent_dir(filepath)

  # Create a temporary file, write the contents of the public key, and move
  # to final destination.
  file_object = tempfile.TemporaryFile()

  # Generate the ed25519 public key file contents in metadata format (i.e.,
  # does not include the keyid portion).
  keytype = ed25519_key['keytype']
  keyval = ed25519_key['keyval']
  scheme = ed25519_key['scheme']
  ed25519key_metadata_format = securesystemslib.keys.format_keyval_to_metadata(
      keytype, scheme, keyval, private=False)

  file_object.write(json.dumps(ed25519key_metadata_format).encode('utf-8'))

  # Write the public key (i.e., 'public', which is in PEM format) to
  # '<filepath>.pub'.  (1) Create a temporary file, (2) write the contents of
  # the public key, and (3) move to final destination.
  # The temporary file is closed after the final move.
  securesystemslib.util.persist_temp_file(file_object, filepath + '.pub')

  # Write the encrypted key string, conformant to
  # 'securesystemslib.formats.ENCRYPTEDKEY_SCHEMA', to '<filepath>'.
  file_object = tempfile.TemporaryFile()

  # Encrypt the private key if 'password' is set.
  if len(password):
    ed25519_key = securesystemslib.keys.encrypt_key(ed25519_key, password)

  else:
    logger.debug('An empty password was given. '
                 'Not encrypting the private key.')
    ed25519_key = json.dumps(ed25519_key)

  # Raise 'securesystemslib.exceptions.CryptoError' if 'ed25519_key' cannot be
  # encrypted.
  file_object.write(ed25519_key.encode('utf-8'))
  securesystemslib.util.persist_temp_file(file_object, filepath)

  return filepath




def import_ed25519_publickey_from_file(filepath):
  """
  <Purpose>
    Load the ED25519 public key object (conformant to
    'securesystemslib.formats.KEY_SCHEMA') stored in 'filepath'.  Return
    'filepath' in securesystemslib.formats.ED25519KEY_SCHEMA format.

    If the key object in 'filepath' contains a private key, it is discarded.

  <Arguments>
    filepath:
      <filepath>.pub file, a public key file.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'filepath' is improperly
    formatted or is an unexpected key type.

  <Side Effects>
    The contents of 'filepath' is read and saved.

  <Returns>
    An ED25519 key object conformant to
    'securesystemslib.formats.ED25519KEY_SCHEMA'.
  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # ED25519 key objects are saved in json and metadata format.  Return the
  # loaded key object in securesystemslib.formats.ED25519KEY_SCHEMA' format that
  # also includes the keyid.
  ed25519_key_metadata = securesystemslib.util.load_json_file(filepath)
  ed25519_key, junk = \
    securesystemslib.keys.format_metadata_to_key(ed25519_key_metadata)

  # Raise an exception if an unexpected key type is imported.  Redundant
  # validation of 'keytype'.  'securesystemslib.keys.format_metadata_to_key()'
  # should have fully validated 'ed25519_key_metadata'.
  if ed25519_key['keytype'] != 'ed25519':
    message = 'Invalid key type loaded: ' + repr(ed25519_key['keytype'])
    raise securesystemslib.exceptions.FormatError(message)

  return ed25519_key





def import_ed25519_privatekey_from_file(filepath, password=None, prompt=False,
    storage_backend=None):
  """
  <Purpose>
    Import the encrypted ed25519 key file in 'filepath', decrypt it, and return
    the key object in 'securesystemslib.formats.ED25519KEY_SCHEMA' format.

    The private key (may also contain the public part) is encrypted with AES
    256 and CTR the mode of operation.  The password is strengthened with
    PBKDF2-HMAC-SHA256.

  <Arguments>
    filepath:
      <filepath> file, an RSA encrypted key file.

    password:
      The password, or passphrase, to import the private key (i.e., the
      encrypted key file 'filepath' must be decrypted before the ed25519 key
      object can be returned.

    prompt:
      If True the user is prompted for a passphrase to decrypt 'filepath'.
      Default is False.

    storage_backend:
      An object which implements
      securesystemslib.storage.StorageBackendInterface. When no object is
      passed a FilesystemBackend will be instantiated and used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted or the imported key object contains an invalid key type (i.e.,
    not 'ed25519').

    securesystemslib.exceptions.CryptoError, if 'filepath' cannot be decrypted.

  <Side Effects>
    'password' is used to decrypt the 'filepath' key file.

  <Returns>
    An ed25519 key object of the form:
    'securesystemslib.formats.ED25519KEY_SCHEMA'.
  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  if password and prompt:
    raise ValueError("Passing 'password' and 'prompt' True is not allowed.")

  if storage_backend is None:
    storage_backend = securesystemslib.storage.FilesystemBackend()

  # If 'password' was passed check format and that it is not empty.
  if password is not None:
    securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

    # TODO: PASSWORD_SCHEMA should be securesystemslib.schema.AnyString(min=1)
    if not len(password):
      raise ValueError('Password must be 1 or more characters')

  elif prompt:
    # Password confirmation disabled here, which should ideally happen only
    # when creating encrypted key files (i.e., improve usability).
    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    # NOTE: A user who gets prompted for a password, can only signal that the
    # key is not encrypted by entering no password in the prompt, as opposed
    # to a programmer who can call the function with or without a 'password'.
    # Hence, we treat an empty password here, as if no 'password' was passed.
    password = get_password('Enter a password for an encrypted RSA'
        ' file \'' + TERM_RED + filepath + TERM_RESET + '\': ',
        confirm=False)

    # If user sets an empty string for the password, explicitly set the
    # password to None, because some functions may expect this later.
    if len(password) == 0:
      password = None

  # Finally, regardless of password, try decrypting the key, if necessary.
  # Otherwise, load it straight from storage.
  with storage_backend.get(filepath) as file_object:
    json_str = file_object.read()

  return securesystemslib.keys.\
      import_ed25519key_from_private_json(json_str, password=password)





def generate_and_write_ecdsa_keypair(filepath=None, password=None):
  """
  <Purpose>
    Generate an ECDSA keypair, where the encrypted key (using 'password' as the
    passphrase) is saved to <'filepath'>.  The public key portion of the
    generated ECDSA key is saved to <'filepath'>.pub.  If the filepath is not
    given, the KEYID is used as the filename and the keypair saved to the
    current working directory.

    The 'cryptography' library is currently supported.  The private key is
    encrypted according to 'cryptography's approach: "Encrypt using the best
    available encryption for a given key's backend. This is a curated
    encryption choice and the algorithm may change over time."

  <Arguments>
    filepath:
      The public and private key files are saved to <filepath>.pub and
      <filepath>, respectively.  If the filepath is not given, the public and
      private keys are saved to the current working directory as <KEYID>.pub
      and <KEYID>.  KEYID is the generated key's KEYID.

    password:
      The password, or passphrase, to encrypt the private portion of the
      generated ECDSA key.  A symmetric encryption key is derived from
      'password', so it is not directly used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if 'filepath' cannot be encrypted.

  <Side Effects>
    Writes key files to '<filepath>' and '<filepath>.pub'.

  <Returns>
    The 'filepath' of the written key.
  """

  # Generate a new ECDSA key object.  The 'cryptography' library is currently
  # supported and performs the actual cryptographic operations.
  ecdsa_key = securesystemslib.keys.generate_ecdsa_key()

  if not filepath:
    filepath = os.path.join(os.getcwd(), ecdsa_key['keyid'])

  else:
    logger.debug('The filepath has been specified.  Not using the key\'s'
        ' KEYID as the default filepath.')

  # Does 'filepath' have the correct format?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # If the caller does not provide a password argument, prompt for one.
  if password is None:

    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    password = get_password('Enter a password for the ECDSA'
        ' key (' + TERM_RED + filepath + TERM_RESET + '): ',
        confirm=True)

  else:
    logger.debug('The password has been specified.  Not prompting for one')

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  # If the parent directory of filepath does not exist,
  # create it (and all its parent directories, if necessary).
  securesystemslib.util.ensure_parent_dir(filepath)

  # Create a temporary file, write the contents of the public key, and move
  # to final destination.
  file_object = tempfile.TemporaryFile()

  # Generate the ECDSA public key file contents in metadata format (i.e., does
  # not include the keyid portion).
  keytype = ecdsa_key['keytype']
  keyval = ecdsa_key['keyval']
  scheme = ecdsa_key['scheme']
  ecdsakey_metadata_format = securesystemslib.keys.format_keyval_to_metadata(
      keytype, scheme, keyval, private=False)

  file_object.write(json.dumps(ecdsakey_metadata_format).encode('utf-8'))

  # Write the public key (i.e., 'public', which is in PEM format) to
  # '<filepath>.pub'.  (1) Create a temporary file, (2) write the contents of
  # the public key, and (3) move to final destination.
  securesystemslib.util.persist_temp_file(file_object, filepath + '.pub')

  # Write the encrypted key string, conformant to
  # 'securesystemslib.formats.ENCRYPTEDKEY_SCHEMA', to '<filepath>'.
  file_object = tempfile.TemporaryFile()
  # Raise 'securesystemslib.exceptions.CryptoError' if 'ecdsa_key' cannot be
  # encrypted.
  encrypted_key = securesystemslib.keys.encrypt_key(ecdsa_key, password)
  file_object.write(encrypted_key.encode('utf-8'))
  securesystemslib.util.persist_temp_file(file_object, filepath)

  return filepath




def import_ecdsa_publickey_from_file(filepath):
  """
  <Purpose>
    Load the ECDSA public key object (conformant to
    'securesystemslib.formats.KEY_SCHEMA') stored in 'filepath'.  Return
    'filepath' in securesystemslib.formats.ECDSAKEY_SCHEMA format.

    If the key object in 'filepath' contains a private key, it is discarded.

  <Arguments>
    filepath:
      <filepath>.pub file, a public key file.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'filepath' is improperly
    formatted or is an unexpected key type.

  <Side Effects>
    The contents of 'filepath' is read and saved.

  <Returns>
    An ECDSA key object conformant to
    'securesystemslib.formats.ECDSAKEY_SCHEMA'.
  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # ECDSA key objects are saved in json and metadata format.  Return the
  # loaded key object in securesystemslib.formats.ECDSAKEY_SCHEMA' format that
  # also includes the keyid.
  ecdsa_key_metadata = securesystemslib.util.load_json_file(filepath)
  ecdsa_key, junk = \
    securesystemslib.keys.format_metadata_to_key(ecdsa_key_metadata)

  return ecdsa_key





def import_ecdsa_privatekey_from_file(filepath, password=None,
    storage_backend=None):
  """
  <Purpose>
    Import the encrypted ECDSA key file in 'filepath', decrypt it, and return
    the key object in 'securesystemslib.formats.ECDSAKEY_SCHEMA' format.

    The 'cryptography' library is currently supported and performs the actual
    cryptographic routine.

  <Arguments>
    filepath:
      <filepath> file, an ECDSA encrypted key file.

    password:
      The password, or passphrase, to import the private key (i.e., the
      encrypted key file 'filepath' must be decrypted before the ECDSA key
      object can be returned.

    storage_backend:
      An object which implements
      securesystemslib.storage.StorageBackendInterface. When no object is
      passed a FilesystemBackend will be instantiated and used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted or the imported key object contains an invalid key type (i.e.,
    not 'ecdsa').

    securesystemslib.exceptions.CryptoError, if 'filepath' cannot be decrypted.

  <Side Effects>
    'password' is used to decrypt the 'filepath' key file.

  <Returns>
    An ECDSA key object of the form: 'securesystemslib.formats.ECDSAKEY_SCHEMA'.
  """

  # Does 'filepath' have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.PATH_SCHEMA.check_match(filepath)

  # If the caller does not provide a password argument, prompt for one.
  # Password confirmation disabled here, which should ideally happen only
  # when creating encrypted key files (i.e., improve usability).
  if password is None:

    # It is safe to specify the full path of 'filepath' in the prompt and not
    # worry about leaking sensitive information about the key's location.
    # However, care should be taken when including the full path in exceptions
    # and log files.
    password = get_password('Enter a password for the encrypted ECDSA'
        ' key (' + TERM_RED + filepath + TERM_RESET + '): ',
        confirm=False)

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  if storage_backend is None:
    storage_backend = securesystemslib.storage.FilesystemBackend()

  # Store the encrypted contents of 'filepath' prior to calling the decryption
  # routine.
  encrypted_key = None

  with storage_backend.get(filepath) as file_object:
    encrypted_key = file_object.read()

  # Decrypt the loaded key file, calling the 'cryptography' library to generate
  # the derived encryption key from 'password'.  Raise
  # 'securesystemslib.exceptions.CryptoError' if the decryption fails.
  key_object = securesystemslib.keys.decrypt_key(encrypted_key.decode('utf-8'),
      password)

  # Raise an exception if an unexpected key type is imported.
  # NOTE: we support keytype's of ecdsa-sha2-nistp256 and ecdsa-sha2-nistp384
  # in order to support key files generated with older versions of
  # securesystemslib. At some point this backwards compatibility should be
  # removed.
  if key_object['keytype'] not in['ecdsa', 'ecdsa-sha2-nistp256',
      'ecdsa-sha2-nistp384']:
    message = 'Invalid key type loaded: ' + repr(key_object['keytype'])
    raise securesystemslib.exceptions.FormatError(message)

  # Add "keyid_hash_algorithms" so that equal ecdsa keys with different keyids
  # can be associated using supported keyid_hash_algorithms.
  key_object['keyid_hash_algorithms'] = \
      securesystemslib.settings.HASH_ALGORITHMS

  return key_object



def import_publickeys_from_file(filepaths, key_types=None):
  """Imports multiple public keys from files.

  NOTE: Use 'import_rsa_publickey_from_file' to specify any other than the
  default signing schemes for an RSA key.

  Arguments:
    filepaths: A list of paths to public key files.
    key_types (optional): A list of types of keys to be imported associated
      with filepaths by index. Must be one of KEY_TYPE_RSA, KEY_TYPE_ED25519 or
      KEY_TYPE_ECDSA. If not specified, all keys are assumed to be
      KEY_TYPE_RSA.

  Raises:
    TypeError: filepaths or key_types (if passed) is not iterable.
    FormatError: key_types is passed and does not have the same length as
        filepaths or contains an unsupported key type.
    See import_ed25519_publickey_from_file, import_rsa_publickey_from_file and
    import_ecdsa_publickey_from_file for other exceptions.

  Returns:
    A dict of public keys in KEYDICT_SCHEMA format.

  """
  if key_types is None:
    key_types = [KEY_TYPE_RSA] * len(filepaths)

  if len(key_types) != len(filepaths):
    raise securesystemslib.exceptions.FormatError(
        "Pass equal amount of 'filepaths' (got {}) and 'key_types (got {}), "
        "or no 'key_types' at all to default to '{}'.".format(
        len(filepaths), len(key_types), KEY_TYPE_RSA))

  key_dict = {}
  for idx, filepath in enumerate(filepaths):
    if key_types[idx] == KEY_TYPE_ED25519:
      key = import_ed25519_publickey_from_file(filepath)

    elif key_types[idx] == KEY_TYPE_RSA:
      key = import_rsa_publickey_from_file(filepath)

    elif key_types[idx] == KEY_TYPE_ECDSA:
      key = import_ecdsa_publickey_from_file(filepath)

    else:
      raise securesystemslib.exceptions.FormatError(
          "Unsupported key type '{}'. Must be '{}', '{}' or '{}'.".format(
          key_types[idx], KEY_TYPE_RSA, KEY_TYPE_ED25519, KEY_TYPE_ECDSA))

    key_dict[key["keyid"]] = key

  return key_dict


if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running interface.py as a standalone module:
  # $ python interface.py.
  import doctest
  doctest.testmod()
