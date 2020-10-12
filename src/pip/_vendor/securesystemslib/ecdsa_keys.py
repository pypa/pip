"""
<Program Name>
  ecdsa_keys.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  November 22, 2016.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support ECDSA keys and signatures.  ECDSA is an
  elliptic-curve digital signature algorithm.  It grants a similar level of
  security as RSA, but uses smaller keys.  No subexponential-time algorithm is
  known for the elliptic curve discrete logarithm problem.

  https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm

  'securesystemslib.ecdsa_keys.py' calls the 'cryptography' library to perform
  all of the ecdsa-related operations.

  The ecdsa-related functions included here are generate(), create_signature()
  and verify_signature().  The 'cryptography' library is used by ecdsa_keys.py
  to perform the actual ECDSA computations, and the functions listed above can
  be viewed as an easy-to-use public interface.
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

import logging

# Import cryptography modules to support ecdsa keys and signatures.
CRYPTO = True
NO_CRYPTO_MSG = "ECDSA key support requires the cryptography library"
try:
  from cryptography.hazmat.backends import default_backend
  from cryptography.hazmat.primitives import hashes
  from cryptography.hazmat.primitives.asymmetric import ec

  from cryptography.hazmat.primitives import serialization
  from cryptography.hazmat.backends.interfaces import PEMSerializationBackend

  from cryptography.hazmat.primitives.serialization import load_pem_public_key
  from cryptography.hazmat.primitives.serialization import load_pem_private_key

  import cryptography.exceptions

  _SCHEME_HASHER = {
    'ecdsa-sha2-nistp256': ec.ECDSA(hashes.SHA256()),
    'ecdsa-sha2-nistp384': ec.ECDSA(hashes.SHA384())
  }

except ImportError:
  CRYPTO = False

# Perform object format-checking and add ability to handle/raise exceptions.
class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions

_SUPPORTED_ECDSA_SCHEMES = ['ecdsa-sha2-nistp256']

logger = logging.getLogger(__name__)


def generate_public_and_private(scheme='ecdsa-sha2-nistp256'):
  """
  <Purpose>
    Generate a pair of ECDSA public and private keys with one of the supported,
    external cryptography libraries.  The public and private keys returned
    conform to 'securesystemslib.formats.PEMECDSA_SCHEMA' and
    'securesystemslib.formats.PEMECDSA_SCHEMA', respectively.

    The public ECDSA public key has the PEM format:
    TODO: should we encrypt the private keys returned here?  Should the
    create_signature() accept encrypted keys?

    '-----BEGIN PUBLIC KEY-----

    ...

    '-----END PUBLIC KEY-----'



    The private ECDSA private key has the PEM format:

    '-----BEGIN EC PRIVATE KEY-----

    ...

    -----END EC PRIVATE KEY-----'

    >>> public, private = generate_public_and_private()
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(public)
    True
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(private)
    True

  <Arguments>
    scheme:
      A string indicating which algorithm to use for the generation of the
      public and private ECDSA keys.  'ecdsa-sha2-nistp256' is the only
      currently supported ECDSA algorithm, which is supported by OpenSSH and
      specified in RFC 5656 (https://tools.ietf.org/html/rfc5656).

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'algorithm' is improperly
    formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if 'scheme' is an
    unsupported algorithm.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    None.

  <Returns>
    A (public, private) tuple that conform to
    'securesystemslib.formats.PEMECDSA_SCHEMA' and
    'securesystemslib.formats.PEMECDSA_SCHEMA', respectively.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'scheme' have the correct format?
  # Verify that 'scheme' is of the correct type, and that it's one of the
  # supported ECDSA .  It must conform to
  # 'securesystemslib.formats.ECDSA_SCHEME_SCHEMA'.  Raise
  # 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.ECDSA_SCHEME_SCHEMA.check_match(scheme)

  public_key = None
  private_key = None

  # An if-clause is strictly not needed, since 'ecdsa_sha2-nistp256' is the
  # only currently supported ECDSA signature scheme.  Nevertheness, include the
  # conditional statement to accomodate any schemes that might be added.
  if scheme == 'ecdsa-sha2-nistp256':
    private_key = ec.generate_private_key(ec.SECP256R1, default_backend())
    public_key = private_key.public_key()

  # The ECDSA_SCHEME_SCHEMA.check_match() above should have detected any
  # invalid 'scheme'.  This is a defensive check.
  else: #pragma: no cover
    raise securesystemslib.exceptions.UnsupportedAlgorithmError('An unsupported'
      ' scheme specified: ' + repr(scheme) + '.\n  Supported'
      ' algorithms: ' + repr(_SUPPORTED_ECDSA_SCHEMES))

  private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption())

  public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo)

  return public_pem.decode('utf-8'), private_pem.decode('utf-8')





def create_signature(public_key, private_key, data, scheme='ecdsa-sha2-nistp256'):
  """
  <Purpose>
    Return a (signature, scheme) tuple.

    >>> requested_scheme = 'ecdsa-sha2-nistp256'
    >>> public, private = generate_public_and_private(requested_scheme)
    >>> data = b'The quick brown fox jumps over the lazy dog'
    >>> signature, scheme = create_signature(public, private, data, requested_scheme)
    >>> securesystemslib.formats.ECDSASIGNATURE_SCHEMA.matches(signature)
    True
    >>> requested_scheme == scheme
    True

  <Arguments>
    public:
      The ECDSA public key in PEM format.

    private:
      The ECDSA private key in PEM format.

    data:
      Byte data used by create_signature() to generate the signature returned.

    scheme:
      The signature scheme used to generate the signature.  For example:
      'ecdsa-sha2-nistp256'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.CryptoError, if a signature cannot be created.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if 'scheme' is not
    one of the supported signature schemes.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    None.

  <Returns>
    A signature dictionary conformat to
    'securesystemslib.format.SIGNATURE_SCHEMA'.  ECDSA signatures are XX bytes,
    however, the hexlified signature is stored in the dictionary returned.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Do 'public_key' and 'private_key' have the correct format?
  # This check will ensure that the arguments conform to
  # 'securesystemslib.formats.PEMECDSA_SCHEMA'.  Raise
  # 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.PEMECDSA_SCHEMA.check_match(public_key)

  # Is 'private_key' properly formatted?
  securesystemslib.formats.PEMECDSA_SCHEMA.check_match(private_key)

  # Is 'scheme' properly formatted?
  securesystemslib.formats.ECDSA_SCHEME_SCHEMA.check_match(scheme)

  # 'ecdsa-sha2-nistp256' is the only currently supported ECDSA scheme, so this
  # if-clause isn't strictly needed.  Nevertheless, the conditional statement
  # is included to accommodate multiple schemes that can potentially be added
  # in the future.
  if scheme == 'ecdsa-sha2-nistp256':
    try:
      private_key = load_pem_private_key(private_key.encode('utf-8'),
        password=None, backend=default_backend())

      signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    except TypeError as e:
      raise securesystemslib.exceptions.CryptoError('Could not create'
        ' signature: ' + str(e))

  # A defensive check for an invalid 'scheme'.  The
  # ECDSA_SCHEME_SCHEMA.check_match() above should have already validated it.
  else: #pragma: no cover
    raise securesystemslib.exceptions.UnsupportedAlgorithmError('Unsupported'
      ' signature scheme is specified: ' + repr(scheme))

  return signature, scheme





def verify_signature(public_key, scheme, signature, data):
  """
  <Purpose>
    Verify that 'signature' was produced by the private key associated with
    'public_key'.

    >>> scheme = 'ecdsa-sha2-nistp256'
    >>> public, private = generate_public_and_private(scheme)
    >>> data = b'The quick brown fox jumps over the lazy dog'
    >>> signature, scheme = create_signature(public, private, data, scheme)
    >>> verify_signature(public, scheme, signature, data)
    True
    >>> verify_signature(public, scheme, signature, b'bad data')
    False

  <Arguments>
    public_key:
      The ECDSA public key in PEM format.  The public key is needed to verify
      'signature'.

    scheme:
      The signature scheme used to generate 'signature'.  For example:
      'ecdsa-sha2-nistp256'.

    signature:
      The signature to be verified, which should have been generated by
      the private key associated with 'public_key'.  'data'.

    data:
      Byte data that was used by create_signature() to generate 'signature'.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if any of the arguments are
    improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if 'scheme' is
    not one of the supported signature schemes.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    None.

  <Returns>
    Boolean, indicating whether the 'signature' of data was generated by
    the private key associated with 'public_key'.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Are the arguments properly formatted?
  # If not, raise 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.PEMECDSA_SCHEMA.check_match(public_key)
  securesystemslib.formats.ECDSA_SCHEME_SCHEMA.check_match(scheme)
  securesystemslib.formats.ECDSASIGNATURE_SCHEMA.check_match(signature)

  ecdsa_key = load_pem_public_key(public_key.encode('utf-8'),
      backend=default_backend())

  if not isinstance(ecdsa_key, ec.EllipticCurvePublicKey):
    raise securesystemslib.exceptions.FormatError('Invalid ECDSA public'
      ' key: ' + repr(public_key))

  else:
    logger.debug('Loaded a valid ECDSA public key.')

  # verify() raises an 'InvalidSignature' exception if 'signature'
  # is invalid.
  try:
    ecdsa_key.verify(signature, data, _SCHEME_HASHER[scheme])
    return True

  except (TypeError, cryptography.exceptions.InvalidSignature):
    return False





def create_ecdsa_public_and_private_from_pem(pem, password=None):
  """
  <Purpose>
    Create public and private ECDSA keys from a private 'pem'.  The public and
    private keys are strings in PEM format:

    public: '-----BEGIN PUBLIC KEY----- ... -----END PUBLIC KEY-----',
    private: '-----BEGIN EC PRIVATE KEY----- ... -----END EC PRIVATE KEY-----'}}

    >>> junk, private = generate_public_and_private()
    >>> public, private = create_ecdsa_public_and_private_from_pem(private)
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(public)
    True
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(private)
    True
    >>> passphrase = 'secret'
    >>> encrypted_pem = create_ecdsa_encrypted_pem(private, passphrase)
    >>> public, private = create_ecdsa_public_and_private_from_pem(encrypted_pem, passphrase)
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(public)
    True
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(private)
    True

  <Arguments>
    pem:
      A string in PEM format.  The private key is extracted and returned in
      an ecdsakey object.

    password: (optional)
      The password, or passphrase, to decrypt the private part of the ECDSA key
      if it is encrypted.  'password' is not used directly as the encryption
      key, a stronger encryption key is derived from it.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if the ECDSA key
    pair could not be extracted, possibly due to an unsupported algorithm.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    None.

  <Returns>
    A dictionary containing the ECDSA keys and other identifying information.
    Conforms to 'securesystemslib.formats.ECDSAKEY_SCHEMA'.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'pem' have the correct format?
  # This check will ensure 'pem' conforms to
  # 'securesystemslib.formats.ECDSARSA_SCHEMA'.
  securesystemslib.formats.PEMECDSA_SCHEMA.check_match(pem)

  if password is not None:
    securesystemslib.formats.PASSWORD_SCHEMA.check_match(password)
    password = password.encode('utf-8')

  else:
    logger.debug('The password/passphrase is unset.  The PEM is expected'
      ' to be unencrypted.')

  public = None
  private = None

  # Generate the public and private ECDSA keys.  The pyca/cryptography library
  # performs the actual import operation.
  try:
    private = load_pem_private_key(pem.encode('utf-8'), password=password,
      backend=default_backend())

  except (ValueError, cryptography.exceptions.UnsupportedAlgorithm) as e:
    raise securesystemslib.exceptions.CryptoError('Could not import private'
      ' PEM.\n' + str(e))

  public = private.public_key()

  # Serialize public and private keys to PEM format.
  private = private.private_bytes(encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption())

  public = public.public_bytes(encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo)

  return public.decode('utf-8'), private.decode('utf-8')





def create_ecdsa_encrypted_pem(private_pem, passphrase):
  """
  <Purpose>
    Return a string in PEM format, where the private part of the ECDSA key is
    encrypted. The private part of the ECDSA key is encrypted as done by
    pyca/cryptography: "Encrypt using the best available encryption for a given
    key's backend. This is a curated encryption choice and the algorithm may
    change over time."

    >>> junk, private = generate_public_and_private()
    >>> passphrase = 'secret'
    >>> encrypted_pem = create_ecdsa_encrypted_pem(private, passphrase)
    >>> securesystemslib.formats.PEMECDSA_SCHEMA.matches(encrypted_pem)
    True

  <Arguments>
    private_pem:
    The private ECDSA key string in PEM format.

    passphrase:
    The passphrase, or password, to encrypt the private part of the ECDSA
    key. 'passphrase' is not used directly as the encryption key, a stronger
    encryption key is derived from it.

    <Exceptions>
      securesystemslib.exceptions.FormatError, if the arguments are improperly
      formatted.

      securesystemslib.exceptions.CryptoError, if an ECDSA key in encrypted PEM
      format cannot be created.

    securesystemslib.exceptions.UnsupportedLibraryError, if the cryptography
    module is not available.

  <Side Effects>
    None.

  <Returns>
    A string in PEM format, where the private RSA portion is encrypted.
    Conforms to 'securesystemslib.formats.PEMECDSA_SCHEMA'.
  """

  if not CRYPTO: # pragma: no cover
    raise securesystemslib.exceptions.UnsupportedLibraryError(NO_CRYPTO_MSG)

  # Does 'private_key' have the correct format?
  # Raise 'securesystemslib.exceptions.FormatError' if the check fails.
  securesystemslib.formats.PEMRSA_SCHEMA.check_match(private_pem)

  # Does 'passphrase' have the correct format?
  securesystemslib.formats.PASSWORD_SCHEMA.check_match(passphrase)

  encrypted_pem = None

  private = load_pem_private_key(private_pem.encode('utf-8'), password=None,
    backend=default_backend())

  encrypted_private_pem = \
    private.private_bytes(encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode('utf-8')))

  return encrypted_private_pem



if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running 'ecdsa_keys.py' as a standalone module.
  # python -B ecdsa_keys.py
  import doctest
  doctest.testmod()
