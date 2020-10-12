"""
<Program Name>
  ed25519_keys.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  September 24, 2013.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support Ed25519 signatures.  Ed25519 is an
  elliptic-curve public key signature scheme, its main strength being small
  signatures (64 bytes) and small public keys (32 bytes).
  http://ed25519.cr.yp.to/

  'securesystemslib/ed25519_keys.py' calls 'ed25519.py', which is the pure
  Python implementation of ed25519 optimized for a faster runtime.  The Python
  reference implementation is concise, but very slow (verifying signatures
  takes ~9 seconds on an Intel core 2 duo @ 2.2 ghz x 2).  The optimized
  version can verify signatures in ~2 seconds.

  http://ed25519.cr.yp.to/software.html
  https://github.com/pyca/ed25519

  Optionally, ed25519 cryptographic operations may be executed by PyNaCl, which
  is a Python binding to the NaCl library and is faster than the pure python
  implementation.  Verifying signatures can take approximately 0.0009 seconds.
  PyNaCl relies on the libsodium C library.  PyNaCl is required for key and
  signature generation.  Verifying signatures may be done in pure Python.

  https://github.com/pyca/pynacl
  https://github.com/jedisct1/libsodium
  http://nacl.cr.yp.to/
  https://github.com/pyca/ed25519

  The ed25519-related functions included here are generate(), create_signature()
  and verify_signature().  The 'ed25519' and PyNaCl (i.e., 'nacl') modules used
  by ed25519_keys.py perform the actual ed25519 computations and the functions
  listed above can be viewed as an easy-to-use public interface.
 """

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# 'binascii' required for hexadecimal conversions.  Signatures and
# public/private keys are hexlified.
import binascii

# TODO:  The 'warnings' module needed to temporarily suppress user warnings
# raised by 'pynacl' (as of version 0.2.3).  Warnings temporarily suppressed
# here to avoid confusing users with an unexpected error message that gives
# no indication of its source.  These warnings are printed when using
# the repository tools, including for clients that request an update.
# http://docs.python.org/2/library/warnings.html#temporarily-suppressing-warnings
import warnings

# 'os' required to generate OS-specific randomness (os.urandom) suitable for
# cryptographic use.
# http://docs.python.org/2/library/os.html#miscellaneous-functions
import os

# Import the python implementation of the ed25519 algorithm provided by pyca,
# which is an optimized version of the one provided by ed25519's authors.
# Note: The pure Python version does not include protection against side-channel
# attacks.  Verifying signatures can take approximately 2 seconds on an intel
# core 2 duo @ 2.2 ghz x 2).  Optionally, the PyNaCl module may be used to
# speed up ed25519 cryptographic operations.
# http://ed25519.cr.yp.to/software.html
# https://github.com/pyca/ed25519
# https://github.com/pyca/pynacl
#
# Import the PyNaCl library, if available.  It is recommended this library be
# used over the pure python implementation of Ed25519, due to its speedier
# routines and side-channel protections available in the libsodium library.
NACL = True
NO_NACL_MSG = "ed25519 key support requires the nacl library"
try:
  import nacl.signing
  import nacl.encoding
except ImportError:
    NACL = False

# The optimized pure Python implementation of Ed25519.  If
# PyNaCl cannot be imported and an attempt to use is made in this module, a
# 'securesystemslib.exceptions.UnsupportedLibraryError' exception is raised.
from pip._vendor.securesystemslib._vendor.ed25519 import ed25519

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions

# Supported ed25519 signing schemes: 'ed25519'.  The pure Python implementation
# (i.e., ed25519') and PyNaCl (i.e., 'nacl', libsodium + Python bindings)
# modules are currently supported in the creation of 'ed25519' signatures.
# Previously, a distinction was made between signatures made by the pure Python
# implementation and PyNaCl.
_SUPPORTED_ED25519_SIGNING_SCHEMES = ['ed25519']


def generate_public_and_private():
  """
  <Purpose>
    Generate a pair of ed25519 public and private keys with PyNaCl.  The public
    and private keys returned conform to
    'securesystemslib.formats.ED25519PULIC_SCHEMA' and
    'securesystemslib.formats.ED25519SEED_SCHEMA', respectively, and have the
    form:

    '\xa2F\x99\xe0\x86\x80%\xc8\xee\x11\xb95T\xd9\...'

    An ed25519 seed key is a random 32-byte string.  Public keys are also 32
    bytes.

    >>> public, private = generate_public_and_private()
    >>> securesystemslib.formats.ED25519PUBLIC_SCHEMA.matches(public)
    True
    >>> securesystemslib.formats.ED25519SEED_SCHEMA.matches(private)
    True

  <Arguments>
    None.

  <Exceptions>
    securesystemslib.exceptions.UnsupportedLibraryError, if the PyNaCl ('nacl')
    module is unavailable.

    NotImplementedError, if a randomness source is not found by 'os.urandom'.

  <Side Effects>
    The ed25519 keys are generated by first creating a random 32-byte seed
    with os.urandom() and then calling PyNaCl's nacl.signing.SigningKey().

  <Returns>
    A (public, private) tuple that conform to
    'securesystemslib.formats.ED25519PUBLIC_SCHEMA' and
    'securesystemslib.formats.ED25519SEED_SCHEMA', respectively.
  """

  if not NACL: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_NACL_MSG)

  # Generate ed25519's seed key by calling os.urandom().  The random bytes
  # returned should be suitable for cryptographic use and is OS-specific.
  # Raise 'NotImplementedError' if a randomness source is not found.
  # ed25519 seed keys are fixed at 32 bytes (256-bit keys).
  # http://blog.mozilla.org/warner/2011/11/29/ed25519-keys/
  seed = os.urandom(32)
  public = None

  # Generate the public key.  PyNaCl (i.e., 'nacl' module) performs the actual
  # key generation.
  nacl_key = nacl.signing.SigningKey(seed)
  public = nacl_key.verify_key.encode(encoder=nacl.encoding.RawEncoder())

  return public, seed



def create_signature(public_key, private_key, data, scheme):
  """
  <Purpose>
    Return a (signature, scheme) tuple, where the signature scheme is 'ed25519'
    and is always generated by PyNaCl (i.e., 'nacl').  The signature returned
    conforms to 'securesystemslib.formats.ED25519SIGNATURE_SCHEMA', and has the
    form:

    '\xae\xd7\x9f\xaf\x95{bP\x9e\xa8YO Z\x86\x9d...'

    A signature is a 64-byte string.

    >>> public, private = generate_public_and_private()
    >>> data = b'The quick brown fox jumps over the lazy dog'
    >>> scheme = 'ed25519'
    >>> signature, scheme = \
        create_signature(public, private, data, scheme)
    >>> securesystemslib.formats.ED25519SIGNATURE_SCHEMA.matches(signature)
    True
    >>> scheme == 'ed25519'
    True
    >>> signature, scheme = \
        create_signature(public, private, data, scheme)
    >>> securesystemslib.formats.ED25519SIGNATURE_SCHEMA.matches(signature)
    True
    >>> scheme == 'ed25519'
    True

  <Arguments>
    public:
      The ed25519 public key, which is a 32-byte string.

    private:
      The ed25519 private key, which is a 32-byte string.

    data:
      Data object used by create_signature() to generate the signature.

    scheme:
      The signature scheme used to generate the signature.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if a signature cannot be created.

    securesystemslib.exceptions.UnsupportedLibraryError, if the PyNaCl ('nacl')
    module is unavailable.

  <Side Effects>
    nacl.signing.SigningKey.sign() called to generate the actual signature.

  <Returns>
    A signature dictionary conformat to
    'securesystemslib.format.SIGNATURE_SCHEMA'.  ed25519 signatures are 64
    bytes, however, the hexlified signature is stored in the dictionary
    returned.
  """

  if not NACL: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_NACL_MSG)

  # Does 'public_key' have the correct format?
  # This check will ensure 'public_key' conforms to
  # 'securesystemslib.formats.ED25519PUBLIC_SCHEMA', which must have length 32
  # bytes.  Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.ED25519PUBLIC_SCHEMA.check_match(public_key)

  # Is 'private_key' properly formatted?
  securesystemslib.formats.ED25519SEED_SCHEMA.check_match(private_key)

  # Is 'scheme' properly formatted?
  securesystemslib.formats.ED25519_SIG_SCHEMA.check_match(scheme)

  # Signing the 'data' object requires a seed and public key.
  # nacl.signing.SigningKey.sign() generates the signature.
  public = public_key
  private = private_key

  signature = None

  # An if-clause is not strictly needed here, since 'ed25519' is the only
  # currently supported scheme.  Nevertheless, include the conditional
  # statement to accommodate schemes that might be added in the future.
  if scheme == 'ed25519':
    try:
      nacl_key = nacl.signing.SigningKey(private)
      nacl_sig = nacl_key.sign(data)
      signature = nacl_sig.signature

    except (ValueError, TypeError, nacl.exceptions.CryptoError) as e:
      raise securesystemslib.exceptions.CryptoError('An "ed25519" signature'
          ' could not be created with PyNaCl.' + str(e))

  # This is a defensive check for a valid 'scheme', which should have already
  # been validated in the check_match() above.
  else: #pragma: no cover
    raise securesystemslib.exceptions.UnsupportedAlgorithmError('Unsupported'
      ' signature scheme is specified: ' + repr(scheme))

  return signature, scheme





def verify_signature(public_key, scheme, signature, data):
  """
  <Purpose>
    Determine whether the private key corresponding to 'public_key' produced
    'signature'.  verify_signature() will use the public key, the 'scheme' and
    'sig', and 'data' arguments to complete the verification.

    >>> public, private = generate_public_and_private()
    >>> data = b'The quick brown fox jumps over the lazy dog'
    >>> scheme = 'ed25519'
    >>> signature, scheme = \
        create_signature(public, private, data, scheme)
    >>> verify_signature(public, scheme, signature, data)
    True
    >>> bad_data = b'The sly brown fox jumps over the lazy dog'
    >>> bad_signature, scheme = \
        create_signature(public, private, bad_data, scheme)
    >>> verify_signature(public, scheme, bad_signature, data)
    False

  <Arguments>
    public_key:
      The public key is a 32-byte string.

    scheme:
      'ed25519' signature scheme used by either the pure python
      implementation (i.e., ed25519.py) or PyNacl (i.e., 'nacl').

    signature:
      The signature is a 64-byte string.

    data:
      Data object used by securesystemslib.ed25519_keys.create_signature() to
      generate 'signature'.  'data' is needed here to verify the signature.

  <Exceptions>
    securesystemslib.exceptions.UnsupportedAlgorithmError.  Raised if the
    signature scheme 'scheme' is not one supported by
    securesystemslib.ed25519_keys.create_signature().

    securesystemslib.exceptions.FormatError. Raised if the arguments are
    improperly formatted.

  <Side Effects>
    nacl.signing.VerifyKey.verify() called if available, otherwise
    securesystemslib._vendor.ed25519.ed25519.checkvalid() called to do the
    verification.

  <Returns>
    Boolean.  True if the signature is valid, False otherwise.
  """

  # Does 'public_key' have the correct format?
  # This check will ensure 'public_key' conforms to
  # 'securesystemslib.formats.ED25519PUBLIC_SCHEMA', which must have length 32
  # bytes.  Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.ED25519PUBLIC_SCHEMA.check_match(public_key)

  # Is 'scheme' properly formatted?
  securesystemslib.formats.ED25519_SIG_SCHEMA.check_match(scheme)

  # Is 'signature' properly formatted?
  securesystemslib.formats.ED25519SIGNATURE_SCHEMA.check_match(signature)

  # Verify 'signature'.  Before returning the Boolean result, ensure 'ed25519'
  # was used as the signature scheme.
  public = public_key
  valid_signature = False

  if scheme in _SUPPORTED_ED25519_SIGNING_SCHEMES:
    if NACL:
      try:
        nacl_verify_key = nacl.signing.VerifyKey(public)
        nacl_message = nacl_verify_key.verify(data, signature)
        valid_signature = True

      except nacl.exceptions.BadSignatureError:
        pass

    # Verify 'ed25519' signature with the pure Python implementation.
    else:
      try:
        ed25519.checkvalid(signature, data, public)
        valid_signature = True

      # The pure Python implementation raises 'Exception' if 'signature' is
      # invalid.
      except Exception as e:
        pass

  # This is a defensive check for a valid 'scheme', which should have already
  # been validated in the ED25519_SIG_SCHEMA.check_match(scheme) above.
  else: #pragma: no cover
    message = 'Unsupported ed25519 signature scheme: ' + repr(scheme) + '.\n' + \
      'Supported schemes: ' + repr(_SUPPORTED_ED25519_SIGNING_SCHEMES) + '.'
    raise securesystemslib.exceptions.UnsupportedAlgorithmError(message)

  return valid_signature



if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running 'ed25519_keys.py' as a standalone module.
  # python -B ed25519_keys.py
  import doctest
  doctest.testmod()
