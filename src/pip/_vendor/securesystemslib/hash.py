#!/usr/bin/env python2
"""
<Program Name>
  hash.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  February 28, 2012.  Based on a previous version of this module.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Support secure hashing and message digests. Any hash-related routines that
  securesystemslib requires should be located in this module.  Simplifying the
  creation of digest objects, and providing a central location for hash
  routines are the main goals of this module.  Support routines implemented
  include functions to create digest objects given a filename or file object.
  Only the standard hashlib library is currently supported, but
  pyca/cryptography support will be added in the future.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib

from pip._vendor import six

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import storage as _securesystemslib_storage
securesystemslib.storage = _securesystemslib_storage


DEFAULT_CHUNK_SIZE = 4096
DEFAULT_HASH_ALGORITHM = 'sha256'
DEFAULT_HASH_LIBRARY = 'hashlib'
SUPPORTED_LIBRARIES = ['hashlib']


# If `pyca_crypto` is installed, add it to supported libraries
try:
  import cryptography.exceptions
  import cryptography.hazmat.backends
  import cryptography.hazmat.primitives.hashes as _pyca_hashes
  import binascii

  # Dictionary of `pyca/cryptography` supported hash algorithms.
  PYCA_DIGEST_OBJECTS_CACHE = {
    "md5":  _pyca_hashes.MD5,
    "sha1": _pyca_hashes.SHA1,
    "sha224": _pyca_hashes.SHA224,
    "sha256": _pyca_hashes.SHA256,
    "sha384": _pyca_hashes.SHA384,
    "sha512": _pyca_hashes.SHA512
  }

  SUPPORTED_LIBRARIES.append('pyca_crypto')

  class PycaDiggestWrapper(object):
    """
    <Purpose>
      A wrapper around `cryptography.hazmat.primitives.hashes.Hash` which adds
      additional methods to meet expected interface for digest objects:

        digest_object.digest_size
        digest_object.hexdigest()
        digest_object.update('data')
        digest_object.digest()

    <Properties>
      algorithm:
        Specific for `cryptography.hazmat.primitives.hashes.Hash` object, but
        needed for `rsa_keys.py`

      digest_size:
        Returns original's object digest size.

    <Methods>
      digest(self) -> bytes:
        Calls original's object `finalize` method and returns digest as bytes.
        NOTE: `cryptography.hazmat.primitives.hashes.Hash` allows calling
        `finalize` method just once on the same instance, so everytime `digest`
        methods is called, we replace internal object (`_digest_obj`).

      hexdigest(self) -> str:
        Returns a string hex representation of digest.

      update(self, data) -> None:
        Updates digest object data by calling the original's object `update`
        method.
    """

    def __init__(self, digest_obj):
      self._digest_obj = digest_obj

    @property
    def algorithm(self):
      return self._digest_obj.algorithm

    @property
    def digest_size(self):
      return self._digest_obj.algorithm.digest_size

    def digest(self):
      digest_obj_copy = self._digest_obj.copy()
      digest = self._digest_obj.finalize()
      self._digest_obj = digest_obj_copy
      return digest

    def hexdigest(self):
      return binascii.hexlify(self.digest()).decode('utf-8')

    def update(self, data):
      self._digest_obj.update(data)

except ImportError: #pragma: no cover
  pass




def digest(algorithm=DEFAULT_HASH_ALGORITHM, hash_library=DEFAULT_HASH_LIBRARY):
  """
  <Purpose>
    Provide the caller with the ability to create digest objects without having
    to worry about crypto library availability or which library to use.  The
    caller also has the option of specifying which hash algorithm and/or
    library to use.

    # Creation of a digest object using defaults or by specifying hash
    # algorithm and library.
    digest_object = securesystemslib.hash.digest()
    digest_object = securesystemslib.hash.digest('sha384')
    digest_object = securesystemslib.hash.digest('sha256', 'hashlib')

    # The expected interface for digest objects.
    digest_object.digest_size
    digest_object.hexdigest()
    digest_object.update('data')
    digest_object.digest()

    # Added hash routines by this module.
    digest_object = securesystemslib.hash.digest_fileobject(file_object)
    digest_object = securesystemslib.hash.digest_filename(filename)

  <Arguments>
    algorithm:
      The hash algorithm (e.g., 'md5', 'sha1', 'sha256').

    hash_library:
      The crypto library to use for the given hash algorithm (e.g., 'hashlib').

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are
    improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if an unsupported
    hashing algorithm is specified, or digest could not be generated with given
    the algorithm.

    securesystemslib.exceptions.UnsupportedLibraryError, if an unsupported
    library was requested via 'hash_library'.

  <Side Effects>
    None.

  <Returns>
    Digest object

    e.g.
      hashlib.new(algorithm) or
      PycaDiggestWrapper object
  """

  # Are the arguments properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.NAME_SCHEMA.check_match(algorithm)
  securesystemslib.formats.NAME_SCHEMA.check_match(hash_library)

  # Was a hashlib digest object requested and is it supported?
  # If so, return the digest object.
  if hash_library == 'hashlib' and hash_library in SUPPORTED_LIBRARIES:
    try:
      if algorithm == 'blake2b-256':
        return hashlib.new('blake2b', digest_size=32)
      else:
        return hashlib.new(algorithm)

    except (ValueError, TypeError):
      # ValueError: the algorithm value was unknown
      # TypeError: unexpected argument digest_size (on old python)
      raise securesystemslib.exceptions.UnsupportedAlgorithmError(algorithm)

  # Was a pyca_crypto digest object requested and is it supported?
  elif hash_library == 'pyca_crypto' and hash_library in SUPPORTED_LIBRARIES:
    try:
      hash_algorithm = PYCA_DIGEST_OBJECTS_CACHE[algorithm]()
      return PycaDiggestWrapper(
        cryptography.hazmat.primitives.hashes.Hash(hash_algorithm,
            cryptography.hazmat.backends.default_backend()))

    except KeyError:
      raise securesystemslib.exceptions.UnsupportedAlgorithmError(algorithm)

  # The requested hash library is not supported.
  else:
    raise securesystemslib.exceptions.UnsupportedLibraryError('Unsupported'
        ' library requested.  Supported hash'
        ' libraries: ' + repr(SUPPORTED_LIBRARIES))





def digest_fileobject(file_object, algorithm=DEFAULT_HASH_ALGORITHM,
    hash_library=DEFAULT_HASH_LIBRARY, normalize_line_endings=False):
  """
  <Purpose>
    Generate a digest object given a file object.  The new digest object
    is updated with the contents of 'file_object' prior to returning the
    object to the caller.

  <Arguments>
    file_object:
      File object whose contents will be used as the data
      to update the hash of a digest object to be returned.

    algorithm:
      The hash algorithm (e.g., 'md5', 'sha1', 'sha256').

    hash_library:
      The library providing the hash algorithms (e.g., 'hashlib').

    normalize_line_endings: (default False)
      Whether or not to normalize line endings for cross-platform support.
      Note that this results in ambiguous hashes (e.g. 'abc\n' and 'abc\r\n'
      will produce the same hash), so be careful to only apply this to text
      files (not binary), when that equivalence is desirable and cannot result
      in easily-maliciously-corrupted files producing the same hash as a valid
      file.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are
    improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if an unsupported
    hashing algorithm was specified via 'algorithm'.

    securesystemslib.exceptions.UnsupportedLibraryError, if an unsupported
    crypto library was specified via 'hash_library'.

  <Side Effects>
    None.

  <Returns>
    Digest object

    e.g.
      hashlib.new(algorithm) or
      PycaDiggestWrapper object
  """

  # Are the arguments properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.NAME_SCHEMA.check_match(algorithm)
  securesystemslib.formats.NAME_SCHEMA.check_match(hash_library)

  # Digest object returned whose hash will be updated using 'file_object'.
  # digest() raises:
  # securesystemslib.exceptions.UnsupportedAlgorithmError
  # securesystemslib.exceptions.UnsupportedLibraryError
  digest_object = digest(algorithm, hash_library)

  # Defensively seek to beginning, as there's no case where we don't
  # intend to start from the beginning of the file.
  file_object.seek(0)

  # Read the contents of the file object in at most 4096-byte chunks.
  # Update the hash with the data read from each chunk and return after
  # the entire file is processed.
  while True:
    data = file_object.read(DEFAULT_CHUNK_SIZE)
    if not data:
      break

    if normalize_line_endings:
      while data[-1:] == b'\r':
        c = file_object.read(1)
        if not c:
          break

        data += c

      data = (
          data
          # First Windows
          .replace(b'\r\n', b'\n')
          # Then Mac
          .replace(b'\r', b'\n')
      )

    if not isinstance(data, six.binary_type):
      digest_object.update(data.encode('utf-8'))

    else:
      digest_object.update(data)

  return digest_object





def digest_filename(filename, algorithm=DEFAULT_HASH_ALGORITHM,
    hash_library=DEFAULT_HASH_LIBRARY, normalize_line_endings=False,
    storage_backend=None):
  """
  <Purpose>
    Generate a digest object, update its hash using a file object
    specified by filename, and then return it to the caller.

  <Arguments>
    filename:
      The filename belonging to the file object to be used.

    algorithm:
      The hash algorithm (e.g., 'md5', 'sha1', 'sha256').

    hash_library:
      The library providing the hash algorithms (e.g., 'hashlib').

    normalize_line_endings:
      Whether or not to normalize line endings for cross-platform support.

    storage_backend:
      An object which implements
      securesystemslib.storage.StorageBackendInterface. When no object is
      passed a FilesystemBackend will be instantiated and used.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are
    improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if the given
    'algorithm' is unsupported.

    securesystemslib.exceptions.UnsupportedLibraryError, if the given
    'hash_library' is unsupported.

  <Side Effects>
    None.

  <Returns>
    Digest object

    e.g.
      hashlib.new(algorithm) or
      PycaDiggestWrapper object
  """
  # Are the arguments properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.PATH_SCHEMA.check_match(filename)
  securesystemslib.formats.NAME_SCHEMA.check_match(algorithm)
  securesystemslib.formats.NAME_SCHEMA.check_match(hash_library)

  digest_object = None

  if storage_backend is None:
    storage_backend = securesystemslib.storage.FilesystemBackend()

  # Open 'filename' in read+binary mode.
  with storage_backend.get(filename) as file_object:
    # Create digest_object and update its hash data from file_object.
    # digest_fileobject() raises:
    # securesystemslib.exceptions.UnsupportedAlgorithmError
    # securesystemslib.exceptions.UnsupportedLibraryError
    digest_object = digest_fileobject(
        file_object, algorithm, hash_library, normalize_line_endings)

  return digest_object





def digest_from_rsa_scheme(scheme, hash_library=DEFAULT_HASH_LIBRARY):
  """
  <Purpose>
    Get digest object from RSA scheme.

  <Arguments>
    scheme:
      A string that indicates the signature scheme used to generate
      'signature'. Currently supported RSA schemes are defined in
      `securesystemslib.keys.RSA_SIGNATURE_SCHEMES`

    hash_library:
      The crypto library to use for the given hash algorithm (e.g., 'hashlib').

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are
    improperly formatted.

    securesystemslib.exceptions.UnsupportedAlgorithmError, if an unsupported
    hashing algorithm is specified, or digest could not be generated with given
    the algorithm.

    securesystemslib.exceptions.UnsupportedLibraryError, if an unsupported
    library was requested via 'hash_library'.

  <Side Effects>
    None.

  <Returns>
    Digest object

    e.g.
      hashlib.new(algorithm) or
      PycaDiggestWrapper object
  """
  # Are the arguments properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.RSA_SCHEME_SCHEMA.check_match(scheme)

  # Get hash algorithm from rsa scheme (hash algorithm id is specified after
  # the last dash; e.g. rsassa-pss-sha256 -> sha256)
  hash_algorithm = scheme.split('-')[-1]
  return digest(hash_algorithm, hash_library)
