#!/usr/bin/env python

"""
<Program Name>
  rsa_keys.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  June 3, 2015.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support public-key and general-purpose
  cryptography through the pyca/cryptography (available as 'cryptography' on
  pypi) library.

  The RSA-related functions provided include:
  generate_rsa_public_and_private()
  create_rsa_signature()
  verify_rsa_signature()
  create_rsa_encrypted_pem()
  create_rsa_public_and_private_from_pem()

  The general-purpose functions include:
  encrypt_key()
  decrypt_key()

  pyca/cryptography performs the actual cryptographic operations and the
  functions listed above can be viewed as the easy-to-use public interface.

  https://pypi.python.org/pypi/cryptography/
  https://github.com/pyca/cryptography

  https://en.wikipedia.org/wiki/RSA_(algorithm)
  https://en.wikipedia.org/wiki/Advanced_Encryption_Standard
  https://en.wikipedia.org/wiki/PBKDF
  http://en.wikipedia.org/wiki/Scrypt

  securesystemslib key files are encrypted with the AES-256-CTR-Mode symmetric
  key algorithm.  User passwords are strengthened with PBKDF2, currently set to
  100,000 passphrase iterations.  The previous evpy implementation used 1,000
  iterations.

  PEM-encrypted RSA key files use the Triple Data Encryption Algorithm (3DES),
  and Cipher-block chaining (CBC) for the mode of operation.  Password-Based
  Key Derivation Function 1 (PBKF1) + MD5.
 """

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import binascii
import json

CRYPTO = True
NO_CRYPTO_MSG = 'RSA key support requires the cryptography library'
try:
  # Import pyca/cryptography routines needed to generate and load cryptographic
  # keys in PEM format.
  from cryptography.hazmat.primitives import serialization
  from cryptography.hazmat.backends.interfaces import PEMSerializationBackend
  from cryptography.hazmat.primitives.serialization import load_pem_private_key
  from cryptography.hazmat.backends import default_backend

  # Import Exception classes need to catch pyca/cryptography exceptions.
  import cryptography.exceptions

  # 'cryptography.hazmat.primitives.asymmetric' (i.e., pyca/cryptography's
  # public-key cryptography modules) supports algorithms like the Digital
  # Signature Algorithm (DSA) and the ECDSA (Elliptic Curve Digital Signature
  # Algorithm) encryption system.  The 'rsa' module module is needed here to
  # generate RSA keys and PS
  from cryptography.hazmat.primitives.asymmetric import rsa

  # pyca/cryptography requires hash objects to generate PKCS#1 PSS
  # signatures (i.e., padding.PSS).  The 'hmac' module is needed to verify
  # ciphertexts in encrypted key files.
  from cryptography.hazmat.primitives import hashes
  from cryptography.hazmat.primitives import hmac

  # RSA's probabilistic signature scheme with appendix (RSASSA-PSS).
  # PKCS#1 v1.5 is available for compatibility with existing applications, but
  # RSASSA-PSS is encouraged for newer applications.  RSASSA-PSS generates
  # a random salt to ensure the signature generated is probabilistic rather than
  # deterministic (e.g., PKCS#1 v1.5).
  # http://en.wikipedia.org/wiki/RSA-PSS#Schemes
  # https://tools.ietf.org/html/rfc3447#section-8.1
  # The 'padding' module is needed for PSS signatures.
  from cryptography.hazmat.primitives.asymmetric import padding

  # Import pyca/cryptography's Key Derivation Function (KDF) module.
  # 'securesystemslib.keys.py' needs this module to derive a secret key according
  # to the Password-Based Key Derivation Function 2 specification.  The derived
  # key is used as the symmetric key to encrypt securesystemslib key information.
  # PKCS#5 v2.0 PBKDF2 specification: http://tools.ietf.org/html/rfc2898#section-5.2
  from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

  # pyca/cryptography's AES implementation available in 'ciphers.Cipher. and
  # 'ciphers.algorithms'.  AES is a symmetric key algorithm that operates on
  # fixed block sizes of 128-bits.
  # https://en.wikipedia.org/wiki/Advanced_Encryption_Standard
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

  # The mode of operation is presently set to CTR (CounTeR Mode) for symmetric
  # block encryption (AES-256, where the symmetric key is 256 bits).  'modes' can
  # be used as an argument to 'ciphers.Cipher' to specify the mode of operation
  # for the block cipher.  The initial random block, or initialization vector
  # (IV), can be set to begin the process of incrementing the 128-bit blocks and
  # allowing the AES algorithm to perform cipher block operations on them.
  from cryptography.hazmat.primitives.ciphers import modes
except ImportError:
  CRYPTO = False

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import hash as _securesystemslib_hash
securesystemslib.hash = _securesystemslib_hash
from pip._vendor.securesystemslib import util as _securesystemslib_util
securesystemslib.util = _securesystemslib_util

# Extract/reference the cryptography library settings.
from pip._vendor.securesystemslib import settings as _securesystemslib_settings
securesystemslib.settings = _securesystemslib_settings

# Recommended RSA key sizes:
# http://www.emc.com/emc-plus/rsa-labs/historical/twirl-and-rsa-key-size.htm#table1
# According to the document above, revised May 6, 2003, RSA keys of size 3072
# provide security through 2031 and beyond.
_DEFAULT_RSA_KEY_BITS = 3072

# The delimiter symbol used to separate the different sections of encrypted
# files (i.e., salt, iterations, hmac, IV, ciphertext).  This delimiter is
# arbitrarily chosen and should not occur in the hexadecimal representations of
# the fields it is separating.
_ENCRYPTION_DELIMITER = '@@@@'

# AES key size.  Default key size = 32 bytes = AES-256.
_AES_KEY_SIZE = 32

# Default salt size, in bytes.  A 128-bit salt (i.e., a random sequence of data
# to protect against attacks that use precomputed rainbow tables to crack
# password hashes) is generated for PBKDF2.
_SALT_SIZE = 16

# Default PBKDF2 passphrase iterations.  The current "good enough" number
# of passphrase iterations.  We recommend that important keys, such as root,
# be kept offline.  'settings.PBKDF2_ITERATIONS' should increase as CPU
# speeds increase, set here at 100,000 iterations by default (in 2013).
# Repository maintainers may opt to modify the default setting according to
# their security needs and computational restrictions.  A strong user password
# is still important.  Modifying the number of iterations will result in a new
# derived key+PBDKF2 combination if the key is loaded and re-saved, overriding
# any previous iteration setting used by the old '<keyid>.key'.
# https://en.wikipedia.org/wiki/PBKDF2
_PBKDF2_ITERATIONS = securesystemslib.settings.PBKDF2_ITERATIONS





def generate_rsa_public_and_private(bits=_DEFAULT_RSA_KEY_BITS):
  """
  <Purpose>
    Generate public and private RSA keys with modulus length 'bits'.  The
    public and private keys returned conform to
    'securesystemslib.formats.PEMRSA_SCHEMA' and have the form:

    '-----BEGIN RSA PUBLIC KEY----- ...'

    or

    '-----BEGIN RSA PRIVATE KEY----- ...'

    The public and private keys are returned as strings in PEM format.

    'generate_rsa_public_and_private()' enforces a minimum key size of 2048
    bits.  If 'bits' is unspecified, a 3072-bit RSA key is generated, which is
    the key size recommended by TUF.

    >>> public, private = generate_rsa_public_and_private(2048)
    >>> securesystemslib.formats.PEMRSA_SCHEMA.matches(public)
    True
    >>> securesystemslib.formats.PEMRSA_SCHEMA.matches(private)
    True

  <Arguments>
    bits:
      The key size, or key length, of the RSA key.  'bits' must be 2048, or
      greater.  'bits' defaults to 3072 if not specified.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'bits' does not contain the
    correct format.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    The RSA keys are generated from pyca/cryptography's
    rsa.generate_private_key() function.

  <Returns>
    A (public, private) tuple containing the RSA keys in PEM format.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'bits' have the correct format?
  # This check will ensure 'bits' conforms to
  # 'securesystemslib.formats.RSAKEYBITS_SCHEMA'.  'bits' must be an integer
  # object, with a minimum value of 2048.  Raise
  # 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.RSAKEYBITS_SCHEMA.check_match(bits)

  # Generate the public and private RSA keys.  The pyca/cryptography 'rsa'
  # module performs the actual key generation.  The 'bits' argument is used,
  # and a 2048-bit minimum is enforced by
  # securesystemslib.formats.RSAKEYBITS_SCHEMA.check_match().
  private_key = rsa.generate_private_key(public_exponent=65537, key_size=bits,
      backend=default_backend())

  # Extract the public & private halves of the RSA key and generate their
  # PEM-formatted representations.  Return the key pair as a (public, private)
  # tuple, where each RSA is a string in PEM format.
  private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
      format=serialization.PrivateFormat.TraditionalOpenSSL,
      encryption_algorithm=serialization.NoEncryption())

  # Need to generate the public pem from the private key before serialization
  # to PEM.
  public_key = private_key.public_key()
  public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
      format=serialization.PublicFormat.SubjectPublicKeyInfo)

  return public_pem.decode('utf-8'), private_pem.decode('utf-8')





def create_rsa_signature(private_key, data, scheme='rsassa-pss-sha256'):
  """
  <Purpose>
    Generate a 'scheme' signature.  The signature, and the signature scheme
    used, is returned as a (signature, scheme) tuple.

    The signing process will use 'private_key' to generate the signature of
    'data'.

    RFC3447 - RSASSA-PSS
    http://www.ietf.org/rfc/rfc3447.txt

    >>> public, private = generate_rsa_public_and_private(2048)
    >>> data = 'The quick brown fox jumps over the lazy dog'.encode('utf-8')
    >>> scheme = 'rsassa-pss-sha256'
    >>> signature, scheme = create_rsa_signature(private, data, scheme)
    >>> securesystemslib.formats.NAME_SCHEMA.matches(scheme)
    True
    >>> scheme == 'rsassa-pss-sha256'
    True
    >>> securesystemslib.formats.PYCACRYPTOSIGNATURE_SCHEMA.matches(signature)
    True

  <Arguments>
    private_key:
      The private RSA key, a string in PEM format.

    data:
      Data (string) used by create_rsa_signature() to generate the signature.

    scheme:
      The signature scheme used to generate the signature.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'private_key' is improperly
    formatted.

    ValueError, if 'private_key' is unset.

    securesystemslib.exceptions.CryptoError, if the signature cannot be
    generated.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    pyca/cryptography's 'RSAPrivateKey.signer()' called to generate the
    signature.

  <Returns>
    A (signature, scheme) tuple, where the signature is a string and the scheme
    is one of the supported RSA signature schemes. For example:
    'rsassa-pss-sha256'.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does the arguments have the correct format?
  # If not, raise 'securesystemslib.exceptions.FormatError' if any of the
  # checks fail.
  securesystemslib.formats.PEMRSA_SCHEMA.check_match(private_key)
  securesystemslib.formats.DATA_SCHEMA.check_match(data)
  securesystemslib.formats.RSA_SCHEME_SCHEMA.check_match(scheme)

  # Signing 'data' requires a private key. Currently supported RSA signature
  # schemes are defined in `securesystemslib.keys.RSA_SIGNATURE_SCHEMES`.
  signature = None

  # Verify the signature, but only if the private key has been set.  The
  # private key is a NULL string if unset.  Although it may be clearer to
  # explicitly check that 'private_key' is not '', we can/should check for a
  # value and not compare identities with the 'is' keyword.  Up to this point
  # 'private_key' has variable size and can be an empty string.
  if not len(private_key):
    raise ValueError('The required private key is unset.')

  try:
    # 'private_key' (in PEM format) must first be converted to a
    # pyca/cryptography private key object before a signature can be
    # generated.
    private_key_object = load_pem_private_key(private_key.encode('utf-8'),
        password=None, backend=default_backend())

    digest_obj = securesystemslib.hash.digest_from_rsa_scheme(scheme,
        'pyca_crypto')

    if scheme.startswith('rsassa-pss'):
      # Generate an RSSA-PSS signature.  Raise
      # 'securesystemslib.exceptions.CryptoError' for any of the expected
      # exceptions raised by pyca/cryptography.
      signature = private_key_object.sign(
          data, padding.PSS(mgf=padding.MGF1(digest_obj.algorithm),
          salt_length=digest_obj.algorithm.digest_size), digest_obj.algorithm)

    elif scheme.startswith('rsa-pkcs1v15'):
      # Generate an RSA-PKCS1v15 signature.  Raise
      # 'securesystemslib.exceptions.CryptoError' for any of the expected
      # exceptions raised by pyca/cryptography.
      signature = private_key_object.sign(data, padding.PKCS1v15(),
          digest_obj.algorithm)

    # The RSA_SCHEME_SCHEMA.check_match() above should have validated 'scheme'.
    # This is a defensive check check..
    else:  # pragma: no cover
      raise securesystemslib.exceptions.UnsupportedAlgorithmError('Unsupported'
          ' signature scheme is specified: ' + repr(scheme))

  # If the PEM data could not be decrypted, or if its structure could not
  # be decoded successfully.
  except ValueError:
    raise securesystemslib.exceptions.CryptoError('The private key'
        ' (in PEM format) could not be deserialized.')

  # 'TypeError' is raised if a password was given and the private key was
  # not encrypted, or if the key was encrypted but no password was
  # supplied.  Note: A passphrase or password is not used when generating
  # 'private_key', since it should not be encrypted.
  except TypeError:
    raise securesystemslib.exceptions.CryptoError('The private key was'
        ' unexpectedly encrypted.')

  # 'cryptography.exceptions.UnsupportedAlgorithm' is raised if the
  # serialized key is of a type that is not supported by the backend, or if
  # the key is encrypted with a symmetric cipher that is not supported by
  # the backend.
  except cryptography.exceptions.UnsupportedAlgorithm:  # pragma: no cover
    raise securesystemslib.exceptions.CryptoError('The private key is'
        ' encrypted with an unsupported algorithm.')

  return signature, scheme





def verify_rsa_signature(signature, signature_scheme, public_key, data):
  """
  <Purpose>
    Determine whether the corresponding private key of 'public_key' produced
    'signature'.  verify_signature() will use the public key, signature scheme,
    and 'data' to complete the verification.

    >>> public, private = generate_rsa_public_and_private(2048)
    >>> data = b'The quick brown fox jumps over the lazy dog'
    >>> scheme = 'rsassa-pss-sha256'
    >>> signature, scheme = create_rsa_signature(private, data, scheme)
    >>> verify_rsa_signature(signature, scheme, public, data)
    True
    >>> verify_rsa_signature(signature, scheme, public, b'bad_data')
    False

  <Arguments>
    signature:
      A signature, as a string.  This is the signature returned
      by create_rsa_signature().

    signature_scheme:
      A string that indicates the signature scheme used to generate
      'signature'.  Currently supported RSA signature schemes are defined in
      `securesystemslib.keys.RSA_SIGNATURE_SCHEMES`.

    public_key:
      The RSA public key, a string in PEM format.

    data:
      Data used by securesystemslib.keys.create_signature() to generate
      'signature'.  'data' (a string) is needed here to verify 'signature'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'signature',
    'signature_scheme', 'public_key', or 'data' are improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if the signature
    scheme used by 'signature' is not one supported by
    securesystemslib.keys.create_signature().

    securesystemslib.exceptions.CryptoError, if the private key cannot be
    decoded or its key type is unsupported.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    pyca/cryptography's RSAPublicKey.verifier() called to do the actual
    verification.

   <Returns>
    Boolean.  True if the signature is valid, False otherwise.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'public_key' have the correct format?
  # This check will ensure 'public_key' conforms to
  # 'securesystemslib.formats.PEMRSA_SCHEMA'.  Raise
  # 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.PEMRSA_SCHEMA.check_match(public_key)

  # Does 'signature_scheme' have the correct format?
  securesystemslib.formats.RSA_SCHEME_SCHEMA.check_match(signature_scheme)

  # Does 'signature' have the correct format?
  securesystemslib.formats.PYCACRYPTOSIGNATURE_SCHEMA.check_match(signature)

  # What about 'data'?
  securesystemslib.formats.DATA_SCHEMA.check_match(data)

  # Verify whether the private key of 'public_key' produced 'signature'.
  # Before returning the 'valid_signature' Boolean result, ensure 'RSASSA-PSS'
  # was used as the signature scheme.
  valid_signature = False

  # Verify the RSASSA-PSS signature with pyca/cryptography.
  try:
    public_key_object = serialization.load_pem_public_key(
        public_key.encode('utf-8'), backend=default_backend())

    digest_obj = securesystemslib.hash.digest_from_rsa_scheme(signature_scheme,
        'pyca_crypto')

    # verify() raises 'cryptography.exceptions.InvalidSignature' if the
    # signature is invalid. 'salt_length' is set to the digest size of the
    # hashing algorithm.
    try:
      if signature_scheme.startswith('rsassa-pss'):
        public_key_object.verify(signature, data,
            padding.PSS(mgf=padding.MGF1(digest_obj.algorithm),
            salt_length=digest_obj.algorithm.digest_size),
            digest_obj.algorithm)

      elif signature_scheme.startswith('rsa-pkcs1v15'):
        public_key_object.verify(signature, data, padding.PKCS1v15(),
            digest_obj.algorithm)

      # The RSA_SCHEME_SCHEMA.check_match() above should have validated 'scheme'.
      # This is a defensive check check..
      else:  # pragma: no cover
        raise securesystemslib.exceptions.UnsupportedAlgorithmError('Unsupported'
            ' signature scheme is specified: ' + repr(scheme))

      return True

    except cryptography.exceptions.InvalidSignature:
      return False

  # Raised by load_pem_public_key().
  except (ValueError, cryptography.exceptions.UnsupportedAlgorithm) as e:
    raise securesystemslib.exceptions.CryptoError('The PEM could not be'
        ' decoded successfully, or contained an unsupported key type: ' + str(e))





def create_rsa_encrypted_pem(private_key, passphrase):
  """
  <Purpose>
    Return a string in PEM format (TraditionalOpenSSL), where the private part
    of the RSA key is encrypted using the best available encryption for a given
    key's backend. This is a curated (by cryptography.io) encryption choice and
    the algorithm may change over time.

    c.f. cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/
        #cryptography.hazmat.primitives.serialization.BestAvailableEncryption

    >>> public, private = generate_rsa_public_and_private(2048)
    >>> passphrase = 'secret'
    >>> encrypted_pem = create_rsa_encrypted_pem(private, passphrase)
    >>> securesystemslib.formats.PEMRSA_SCHEMA.matches(encrypted_pem)
    True

  <Arguments>
    private_key:
      The private key string in PEM format.

    passphrase:
      The passphrase, or password, to encrypt the private part of the RSA
      key.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
        formatted.

    securesystemslib.exceptions.CryptoError, if the passed RSA key cannot be
        deserialized by pyca cryptography.

    ValueError, if 'private_key' is unset.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.


  <Returns>
    A string in PEM format (TraditionalOpenSSL), where the private RSA key is
    encrypted. Conforms to 'securesystemslib.formats.PEMRSA_SCHEMA'.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # This check will ensure 'private_key' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.PEMRSA_SCHEMA.check_match(private_key)

  # Does 'passphrase' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(passphrase)

  # 'private_key' may still be a NULL string after the
  # 'securesystemslib.formats.PEMRSA_SCHEMA' so we need an additional check
  if len(private_key):
    try:
      private_key = load_pem_private_key(private_key.encode('utf-8'),
          password=None, backend=default_backend())
    except ValueError:
      raise securesystemslib.exceptions.CryptoError('The private key'
          ' (in PEM format) could not be deserialized.')

  else:
    raise ValueError('The required private key is unset.')

  encrypted_pem = private_key.private_bytes(
      encoding=serialization.Encoding.PEM,
      format=serialization.PrivateFormat.TraditionalOpenSSL,
      encryption_algorithm=serialization.BestAvailableEncryption(
      passphrase.encode('utf-8')))

  return encrypted_pem.decode()





def create_rsa_public_and_private_from_pem(pem, passphrase=None):
  """
  <Purpose>
    Generate public and private RSA keys from an optionally encrypted PEM.  The
    public and private keys returned conform to
    'securesystemslib.formats.PEMRSA_SCHEMA' and have the form:

    '-----BEGIN RSA PUBLIC KEY----- ... -----END RSA PUBLIC KEY-----'

    and

    '-----BEGIN RSA PRIVATE KEY----- ...-----END RSA PRIVATE KEY-----'

    The public and private keys are returned as strings in PEM format.

    In case the private key part of 'pem' is encrypted  pyca/cryptography's
    load_pem_private_key() method is passed passphrase.  In the default case
    here, pyca/cryptography will decrypt with a PBKDF1+MD5
    strengthened'passphrase', and 3DES with CBC mode for encryption/decryption.
    Alternatively, key data may be encrypted with AES-CTR-Mode and the
    passphrase strengthened with PBKDF2+SHA256, although this method is used
    only with securesystemslib encrypted key files.

    >>> public, private = generate_rsa_public_and_private(2048)
    >>> passphrase = 'secret'
    >>> encrypted_pem = create_rsa_encrypted_pem(private, passphrase)
    >>> returned_public, returned_private = \
    create_rsa_public_and_private_from_pem(encrypted_pem, passphrase)
    >>> securesystemslib.formats.PEMRSA_SCHEMA.matches(returned_public)
    True
    >>> securesystemslib.formats.PEMRSA_SCHEMA.matches(returned_private)
    True
    >>> public == returned_public
    True
    >>> private == returned_private
    True

  <Arguments>
    pem:
      A byte string in PEM format, where the private key can be encrypted.
      It has the form:

      '-----BEGIN RSA PRIVATE KEY-----\n
      Proc-Type: 4,ENCRYPTED\nDEK-Info: DES-EDE3-CBC ...'

    passphrase: (optional)
      The passphrase, or password, to decrypt the private part of the RSA
      key.  'passphrase' is not directly used as the encryption key, instead
      it is used to derive a stronger symmetric key.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if the public and private RSA keys
    cannot be generated from 'pem', or exported in PEM format.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    pyca/cryptography's 'serialization.load_pem_private_key()' called to
    perform the actual conversion from an encrypted RSA private key to
    PEM format.

  <Returns>
    A (public, private) tuple containing the RSA keys in PEM format.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'encryped_pem' have the correct format?
  # This check will ensure 'pem' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.PEMRSA_SCHEMA.check_match(pem)

  # If passed, does 'passphrase' have the correct format?
  if passphrase is not None:
    securesystemslib.formats.PASSWORD_SCHEMA.check_match(passphrase)
    passphrase = passphrase.encode('utf-8')

  # Generate a pyca/cryptography key object from 'pem'.  The generated
  # pyca/cryptography key contains the required export methods needed to
  # generate the PEM-formatted representations of the public and private RSA
  # key.
  try:
    private_key = load_pem_private_key(pem.encode('utf-8'),
        passphrase, backend=default_backend())

  # pyca/cryptography's expected exceptions for 'load_pem_private_key()':
  # ValueError: If the PEM data could not be decrypted.
  # (possibly because the passphrase is wrong)."
  # TypeError: If a password was given and the private key was not encrypted.
  # Or if the key was encrypted but no password was supplied.
  # UnsupportedAlgorithm: If the private key (or if the key is encrypted with
  # an unsupported symmetric cipher) is not supported by the backend.
  except (ValueError, TypeError, cryptography.exceptions.UnsupportedAlgorithm) as e:
    # Raise 'securesystemslib.exceptions.CryptoError' and pyca/cryptography's
    # exception message.  Avoid propogating pyca/cryptography's exception trace
    # to avoid revealing sensitive error.
    raise securesystemslib.exceptions.CryptoError('RSA (public, private) tuple'
      ' cannot be generated from the encrypted PEM string: ' + str(e))

  # Export the public and private halves of the pyca/cryptography RSA key
  # object.  The (public, private) tuple returned contains the public and
  # private RSA keys in PEM format, as strings.
  # Extract the public & private halves of the RSA key and generate their
  # PEM-formatted representations.  Return the key pair as a (public, private)
  # tuple, where each RSA is a string in PEM format.
  private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
      format=serialization.PrivateFormat.TraditionalOpenSSL,
      encryption_algorithm=serialization.NoEncryption())

  # Need to generate the public key from the private one before serializing
  # to PEM format.
  public_key = private_key.public_key()
  public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
      format=serialization.PublicFormat.SubjectPublicKeyInfo)

  return public_pem.decode(), private_pem.decode()





def encrypt_key(key_object, password):
  """
  <Purpose>
    Return a string containing 'key_object' in encrypted form. Encrypted
    strings may be safely saved to a file.  The corresponding decrypt_key()
    function can be applied to the encrypted string to restore the original key
    object.  'key_object' is a securesystemslib key (e.g., RSAKEY_SCHEMA,
    ED25519KEY_SCHEMA).  This function calls the pyca/cryptography library to
    perform the encryption and derive a suitable encryption key.

    Whereas an encrypted PEM file uses the Triple Data Encryption Algorithm
    (3DES), the Cipher-block chaining (CBC) mode of operation, and the Password
    Based Key Derivation Function 1 (PBKF1) + MD5 to strengthen 'password',
    encrypted securesystemslib keys use AES-256-CTR-Mode and passwords
    strengthened with PBKDF2-HMAC-SHA256 (100K iterations by default, but may
    be overriden in 'settings.PBKDF2_ITERATIONS' by the user).

    http://en.wikipedia.org/wiki/Advanced_Encryption_Standard
    http://en.wikipedia.org/wiki/CTR_mode#Counter_.28CTR.29
    https://en.wikipedia.org/wiki/PBKDF2

    >>> ed25519_key = {'keytype': 'ed25519', \
                       'scheme': 'ed25519', \
                       'keyid': \
          'd62247f817883f593cf6c66a5a55292488d457bcf638ae03207dbbba9dbe457d', \
                       'keyval': {'public': \
          '74addb5ad544a4306b34741bc1175a3613a8d7dc69ff64724243efdec0e301ad', \
                                  'private': \
          '1f26964cc8d4f7ee5f3c5da2fbb7ab35811169573ac367b860a537e47789f8c4'}}
    >>> passphrase = 'secret'
    >>> encrypted_key = encrypt_key(ed25519_key, passphrase)
    >>> securesystemslib.formats.ENCRYPTEDKEY_SCHEMA.matches(encrypted_key.encode('utf-8'))
    True

  <Arguments>
    key_object:
      The securesystemslib key object that should contain the private portion
      of the ED25519 key.

    password:
      The password, or passphrase, to encrypt the private part of the RSA
      key.  'password' is not used directly as the encryption key, a stronger
      encryption key is derived from it.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if any of the arguments are
    improperly formatted or 'key_object' does not contain the private portion
    of the key.

    securesystemslib.exceptions.CryptoError, if an Ed25519 key in encrypted
    securesystemslib format cannot be created.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.


  <Side Effects>
    pyca/Cryptography cryptographic operations called to perform the actual
    encryption of 'key_object'.  'password' used to derive a suitable
    encryption key.

  <Returns>
    An encrypted string in 'securesystemslib.formats.ENCRYPTEDKEY_SCHEMA' format.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Do the arguments have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.ANYKEY_SCHEMA.check_match(key_object)

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  # Ensure the private portion of the key is included in 'key_object'.
  if 'private' not in key_object['keyval'] or not key_object['keyval']['private']:
    raise securesystemslib.exceptions.FormatError('Key object does not contain'
      ' a private part.')

  # Derive a key (i.e., an appropriate encryption key and not the
  # user's password) from the given 'password'.  Strengthen 'password' with
  # PBKDF2-HMAC-SHA256 (100K iterations by default, but may be overriden in
  # 'settings.PBKDF2_ITERATIONS' by the user).
  salt, iterations, derived_key = _generate_derived_key(password)

  # Store the derived key info in a dictionary, the object expected
  # by the non-public _encrypt() routine.
  derived_key_information = {'salt': salt, 'iterations': iterations,
                             'derived_key': derived_key}

  # Convert the key object to json string format and encrypt it with the
  # derived key.
  encrypted_key = _encrypt(json.dumps(key_object), derived_key_information)

  return encrypted_key





def decrypt_key(encrypted_key, password):
  """
  <Purpose>
    Return a string containing 'encrypted_key' in non-encrypted form.
    The decrypt_key() function can be applied to the encrypted string to restore
    the original key object, a securesystemslib key (e.g., RSAKEY_SCHEMA,
    ED25519KEY_SCHEMA). This function calls the appropriate cryptography module
    (i.e., rsa_keys.py) to perform the decryption.

    Encrypted securesystemslib keys use AES-256-CTR-Mode and passwords
    strengthened with PBKDF2-HMAC-SHA256 (100K iterations be default, but may
    be overriden in 'settings.py' by the user).

    http://en.wikipedia.org/wiki/Advanced_Encryption_Standard
    http://en.wikipedia.org/wiki/CTR_mode#Counter_.28CTR.29
    https://en.wikipedia.org/wiki/PBKDF2

    >>> ed25519_key = {'keytype': 'ed25519', \
                       'scheme': 'ed25519', \
                       'keyid': \
          'd62247f817883f593cf6c66a5a55292488d457bcf638ae03207dbbba9dbe457d', \
                       'keyval': {'public': \
          '74addb5ad544a4306b34741bc1175a3613a8d7dc69ff64724243efdec0e301ad', \
                                  'private': \
          '1f26964cc8d4f7ee5f3c5da2fbb7ab35811169573ac367b860a537e47789f8c4'}}
    >>> passphrase = 'secret'
    >>> encrypted_key = encrypt_key(ed25519_key, passphrase)
    >>> decrypted_key = decrypt_key(encrypted_key.encode('utf-8'), passphrase)
    >>> securesystemslib.formats.ED25519KEY_SCHEMA.matches(decrypted_key)
    True
    >>> decrypted_key == ed25519_key
    True

  <Arguments>
    encrypted_key:
      An encrypted securesystemslib key (additional data is also included, such
      as salt, number of password iterations used for the derived encryption
      key, etc) of the form 'securesystemslib.formats.ENCRYPTEDKEY_SCHEMA'.
      'encrypted_key' should have been generated with encrypted_key().

    password:
      The password, or passphrase, to encrypt the private part of the RSA
      key.  'password' is not used directly as the encryption key, a stronger
      encryption key is derived from it.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if a securesystemslib key cannot
    be decrypted from 'encrypted_key'.

    securesystemslib.exceptions.Error, if a valid securesystemslib key object
    is not found in 'encrypted_key'.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    The pyca/cryptography is library called to perform the actual decryption
    of 'encrypted_key'.  The key derivation data stored in 'encrypted_key' is
    used to re-derive the encryption/decryption key.

  <Returns>
    The decrypted key object in 'securesystemslib.formats.ANYKEY_SCHEMA' format.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Do the arguments have the correct format?
  # Ensure the arguments have the appropriate number of objects and object
  # types, and that all dict keys are properly named.
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.ENCRYPTEDKEY_SCHEMA.check_match(encrypted_key)

  # Does 'password' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)

  # Decrypt 'encrypted_key', using 'password' (and additional key derivation
  # data like salts and password iterations) to re-derive the decryption key.
  json_data = _decrypt(encrypted_key, password)

  # Raise 'securesystemslib.exceptions.Error' if 'json_data' cannot be
  # deserialized to a valid 'securesystemslib.formats.ANYKEY_SCHEMA' key
  # object.
  key_object = securesystemslib.util.load_json_string(json_data.decode())

  return key_object





def _generate_derived_key(password, salt=None, iterations=None):
  """
  Generate a derived key by feeding 'password' to the Password-Based Key
  Derivation Function (PBKDF2).  pyca/cryptography's PBKDF2 implementation is
  used in this module.  'salt' may be specified so that a previous derived key
  may be regenerated, otherwise '_SALT_SIZE' is used by default.  'iterations'
  is the number of SHA-256 iterations to perform, otherwise
  '_PBKDF2_ITERATIONS' is used by default.
  """

  # Use pyca/cryptography's default backend (e.g., openSSL, CommonCrypto, etc.)
  # The default backend is not fixed and can be changed by pyca/cryptography
  # over time.
  backend = default_backend()

  # If 'salt' and 'iterations' are unspecified, a new derived key is generated.
  # If specified, a deterministic key is derived according to the given
  # 'salt' and 'iterrations' values.
  if salt is None:
    salt = os.urandom(_SALT_SIZE)

  if iterations is None:
    iterations = _PBKDF2_ITERATIONS

  # Derive an AES key with PBKDF2.  The  'length' is the desired key length of
  # the derived key.
  pbkdf_object = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
       iterations=iterations, backend=backend)

  derived_key = pbkdf_object.derive(password.encode('utf-8'))

  return salt, iterations, derived_key





def _encrypt(key_data, derived_key_information):
  """
  Encrypt 'key_data' using the Advanced Encryption Standard (AES-256) algorithm.
  'derived_key_information' should contain a key strengthened by PBKDF2.  The
  key size is 256 bits and AES's mode of operation is set to CTR (CounTeR Mode).
  The HMAC of the ciphertext is generated to ensure the ciphertext has not been
  modified.

  'key_data' is the JSON string representation of the key.  In the case
  of RSA keys, this format would be 'securesystemslib.formats.RSAKEY_SCHEMA':

  {'keytype': 'rsa',
   'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
              'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

  'derived_key_information' is a dictionary of the form:
    {'salt': '...',
     'derived_key': '...',
     'iterations': '...'}

  'securesystemslib.exceptions.CryptoError' raised if the encryption fails.
  """

  # Generate a random Initialization Vector (IV).  Follow the provably secure
  # encrypt-then-MAC approach, which affords the ability to verify ciphertext
  # without needing to decrypt it and preventing an attacker from feeding the
  # block cipher malicious data.  Modes like GCM provide both encryption and
  # authentication, whereas CTR only provides encryption.

  # Generate a random 128-bit IV.  Random bits of data is needed for salts and
  # initialization vectors suitable for the encryption algorithms used in
  # 'rsa_keys.py'.
  iv = os.urandom(16)

  # Construct an AES-CTR Cipher object with the given key and a randomly
  # generated IV.
  symmetric_key = derived_key_information['derived_key']
  encryptor = Cipher(algorithms.AES(symmetric_key), modes.CTR(iv),
      backend=default_backend()).encryptor()

  # Encrypt the plaintext and get the associated ciphertext.
  # Do we need to check for any exceptions?
  ciphertext = encryptor.update(key_data.encode('utf-8')) + encryptor.finalize()

  # Generate the hmac of the ciphertext to ensure it has not been modified.
  # The decryption routine may verify a ciphertext without having to perform
  # a decryption operation.
  symmetric_key = derived_key_information['derived_key']
  salt = derived_key_information['salt']
  hmac_object = \
    cryptography.hazmat.primitives.hmac.HMAC(symmetric_key, hashes.SHA256(),
        backend=default_backend())
  hmac_object.update(ciphertext)
  hmac_value = binascii.hexlify(hmac_object.finalize())

  # Store the number of PBKDF2 iterations used to derive the symmetric key so
  # that the decryption routine can regenerate the symmetric key successfully.
  # The PBKDF2 iterations are allowed to vary for the keys loaded and saved.
  iterations = derived_key_information['iterations']

  # Return the salt, iterations, hmac, initialization vector, and ciphertext
  # as a single string.  These five values are delimited by
  # '_ENCRYPTION_DELIMITER' to make extraction easier.  This delimiter is
  # arbitrarily chosen and should not occur in the hexadecimal representations
  # of the fields it is separating.
  return binascii.hexlify(salt).decode() + _ENCRYPTION_DELIMITER + \
      str(iterations) + _ENCRYPTION_DELIMITER + \
      hmac_value.decode() + _ENCRYPTION_DELIMITER + \
      binascii.hexlify(iv).decode() + _ENCRYPTION_DELIMITER + \
      binascii.hexlify(ciphertext).decode()





def _decrypt(file_contents, password):
  """
  The corresponding decryption routine for _encrypt().

  'securesystemslib.exceptions.CryptoError' raised if the decryption fails.
  """

  # Extract the salt, iterations, hmac, initialization vector, and ciphertext
  # from 'file_contents'.  These five values are delimited by
  # '_ENCRYPTION_DELIMITER'.  This delimiter is arbitrarily chosen and should
  # not occur in the hexadecimal representations of the fields it is
  # separating.  Raise 'securesystemslib.exceptions.CryptoError', if
  # 'file_contents' does not contains the expected data layout.
  try:
    salt, iterations, hmac, iv, ciphertext = \
      file_contents.split(_ENCRYPTION_DELIMITER)

  except ValueError:
    raise securesystemslib.exceptions.CryptoError('Invalid encrypted file.')

  # Ensure we have the expected raw data for the delimited cryptographic data.
  salt = binascii.unhexlify(salt.encode('utf-8'))
  iterations = int(iterations)
  iv = binascii.unhexlify(iv.encode('utf-8'))
  ciphertext = binascii.unhexlify(ciphertext.encode('utf-8'))

  # Generate derived key from 'password'.  The salt and iterations are
  # specified so that the expected derived key is regenerated correctly.
  # Discard the old "salt" and "iterations" values, as we only need the old
  # derived key.
  junk_old_salt, junk_old_iterations, symmetric_key = \
    _generate_derived_key(password, salt, iterations)

  # Verify the hmac to ensure the ciphertext is valid and has not been altered.
  # See the encryption routine for why we use the encrypt-then-MAC approach.
  # The decryption routine may verify a ciphertext without having to perform
  # a decryption operation.
  generated_hmac_object = \
    cryptography.hazmat.primitives.hmac.HMAC(symmetric_key, hashes.SHA256(),
        backend=default_backend())
  generated_hmac_object.update(ciphertext)
  generated_hmac = binascii.hexlify(generated_hmac_object.finalize())


  if not securesystemslib.util.digests_are_equal(generated_hmac.decode(), hmac):
    raise securesystemslib.exceptions.CryptoError('Decryption failed.')

  # Construct a Cipher object, with the key and iv.
  decryptor = Cipher(algorithms.AES(symmetric_key), modes.CTR(iv),
      backend=default_backend()).decryptor()

  # Decryption gets us the authenticated plaintext.
  plaintext = decryptor.update(ciphertext) + decryptor.finalize()

  return plaintext





if __name__ == '__main__':
  # The interactive sessions of the documentation strings can be tested by
  # running 'rsa_keys.py' as a standalone module:
  # $ python rsa_keys.py
  import doctest
  doctest.testmod()
