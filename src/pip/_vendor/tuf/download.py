#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  download.py

<Started>
  February 21, 2012.  Based on previous version by Geremy Condra.

<Author>
  Konstantin Andrianov
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  Download metadata and target files and check their validity.  The hash and
  length of a downloaded file has to match the hash and length supplied by the
  metadata of that file.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import time
import timeit
import tempfile

from pip._vendor import requests

from pip._vendor import securesystemslib
class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor import six

class _Dummy(object):
  pass
tuf = _Dummy()
from pip._vendor.tuf import exceptions as _tuf_exceptions
tuf.exceptions = _tuf_exceptions
from pip._vendor.tuf import formats as _tuf_formats
tuf.formats = _tuf_formats
from pip._vendor.tuf import settings as _tuf_settings
tuf.settings = _tuf_settings
from pip._vendor.tuf import __version__ as _tuf_version
tuf.__version__ = _tuf_version

from pip._vendor.urllib3.exceptions import ReadTimeoutError

# See 'log.py' to learn how logging is handled in TUF.
logger = logging.getLogger(__name__)

# From http://docs.python-requests.org/en/master/user/advanced/#session-objects:
#
# "The Session object allows you to persist certain parameters across requests.
# It also persists cookies across all requests made from the Session instance,
# and will use urllib3's connection pooling. So if you're making several
# requests to the same host, the underlying TCP connection will be reused,
# which can result in a significant performance increase (see HTTP persistent
# connection)."
#
# NOTE: We use a separate requests.Session per scheme+hostname combination, in
# order to reuse connections to the same hostname to improve efficiency, but
# avoiding sharing state between different hosts-scheme combinations to
# minimize subtle security issues. Some cookies may not be HTTP-safe.
_sessions = {}


def safe_download(url, required_length):
  """
  <Purpose>
    Given the 'url' and 'required_length' of the desired file, open a connection
    to 'url', download it, and return the contents of the file.  Also ensure
    the length of the downloaded file matches 'required_length' exactly.
    tuf.download.unsafe_download() may be called if an upper download limit is
    preferred.

  <Arguments>
    url:
      A URL string that represents the location of the file.

    required_length:
      An integer value representing the length of the file.  This is an exact
      limit.

  <Side Effects>
    A file object is created on disk to store the contents of 'url'.

  <Exceptions>
    tuf.ssl_commons.exceptions.DownloadLengthMismatchError, if there was a
    mismatch of observed vs expected lengths while downloading the file.

    securesystemslib.exceptions.FormatError, if any of the arguments are
    improperly formatted.

    Any other unforeseen runtime exception.

  <Returns>
    A file object that points to the contents of 'url'.
  """

  # Do all of the arguments have the appropriate format?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.URL_SCHEMA.check_match(url)
  tuf.formats.LENGTH_SCHEMA.check_match(required_length)

  return _download_file(url, required_length, STRICT_REQUIRED_LENGTH=True)





def unsafe_download(url, required_length):
  """
  <Purpose>
    Given the 'url' and 'required_length' of the desired file, open a connection
    to 'url', download it, and return the contents of the file.  Also ensure
    the length of the downloaded file is up to 'required_length', and no larger.
    tuf.download.safe_download() may be called if an exact download limit is
    preferred.

  <Arguments>
    url:
      A URL string that represents the location of the file.

    required_length:
      An integer value representing the length of the file.  This is an upper
      limit.

  <Side Effects>
    A file object is created on disk to store the contents of 'url'.

  <Exceptions>
    tuf.ssl_commons.exceptions.DownloadLengthMismatchError, if there was a
    mismatch of observed vs expected lengths while downloading the file.

    securesystemslib.exceptions.FormatError, if any of the arguments are
    improperly formatted.

    Any other unforeseen runtime exception.

  <Returns>
    A file object that points to the contents of 'url'.
  """

  # Do all of the arguments have the appropriate format?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.URL_SCHEMA.check_match(url)
  tuf.formats.LENGTH_SCHEMA.check_match(required_length)

  return _download_file(url, required_length, STRICT_REQUIRED_LENGTH=False)





def _download_file(url, required_length, STRICT_REQUIRED_LENGTH=True):
  """
  <Purpose>
    Given the url and length of the desired file, this function opens a
    connection to 'url' and downloads the file while ensuring its length
    matches 'required_length' if 'STRICT_REQUIRED_LENGH' is True (If False,
    the file's length is not checked and a slow retrieval exception is raised
    if the downloaded rate falls below the acceptable rate).

  <Arguments>
    url:
      A URL string that represents the location of the file.

    required_length:
      An integer value representing the length of the file.

    STRICT_REQUIRED_LENGTH:
      A Boolean indicator used to signal whether we should perform strict
      checking of required_length. True by default. We explicitly set this to
      False when we know that we want to turn this off for downloading the
      timestamp metadata, which has no signed required_length.

  <Side Effects>
    A file object is created on disk to store the contents of 'url'.

  <Exceptions>
    tuf.exceptions.DownloadLengthMismatchError, if there was a
    mismatch of observed vs expected lengths while downloading the file.

    securesystemslib.exceptions.FormatError, if any of the arguments are
    improperly formatted.

    Any other unforeseen runtime exception.

  <Returns>
    A file object that points to the contents of 'url'.
  """

  # Do all of the arguments have the appropriate format?
  # Raise 'securesystemslib.exceptions.FormatError' if there is a mismatch.
  securesystemslib.formats.URL_SCHEMA.check_match(url)
  tuf.formats.LENGTH_SCHEMA.check_match(required_length)

  # 'url.replace('\\', '/')' is needed for compatibility with Windows-based
  # systems, because they might use back-slashes in place of forward-slashes.
  # This converts it to the common format.  unquote() replaces %xx escapes in a
  # url with their single-character equivalent.  A back-slash may be encoded as
  # %5c in the url, which should also be replaced with a forward slash.
  url = six.moves.urllib.parse.unquote(url).replace('\\', '/')
  logger.info('Downloading: ' + repr(url))

  # This is the temporary file that we will return to contain the contents of
  # the downloaded file.
  temp_file = tempfile.TemporaryFile()

  try:
    # Use a different requests.Session per schema+hostname combination, to
    # reuse connections while minimizing subtle security issues.
    parsed_url = six.moves.urllib.parse.urlparse(url)

    if not parsed_url.scheme or not parsed_url.hostname:
      raise tuf.exceptions.URLParsingError(
          'Could not get scheme and hostname from URL: ' + url)

    session_index = parsed_url.scheme + '+' + parsed_url.hostname

    logger.debug('url: ' + url)
    logger.debug('session index: ' + session_index)

    session = _sessions.get(session_index)

    if not session:
      session = requests.Session()
      _sessions[session_index] = session

      # Attach some default headers to every Session.
      requests_user_agent = session.headers['User-Agent']
      # Follows the RFC: https://tools.ietf.org/html/rfc7231#section-5.5.3
      tuf_user_agent = 'tuf/' + tuf.__version__ + ' ' + requests_user_agent
      session.headers.update({
          # Tell the server not to compress or modify anything.
          # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding#Directives
          'Accept-Encoding': 'identity',
          # The TUF user agent.
          'User-Agent': tuf_user_agent})

      logger.debug('Made new session for ' + session_index)

    else:
      logger.debug('Reusing session for ' + session_index)

    # Get the requests.Response object for this URL.
    #
    # Defer downloading the response body with stream=True.
    # Always set the timeout. This timeout value is interpreted by requests as:
    #  - connect timeout (max delay before first byte is received)
    #  - read (gap) timeout (max delay between bytes received)
    with session.get(url, stream=True,
        timeout=tuf.settings.SOCKET_TIMEOUT) as response:

      # Check response status.
      response.raise_for_status()

      # Download the contents of the URL, up to the required length, to a
      # temporary file, and get the total number of downloaded bytes.
      total_downloaded, average_download_speed = \
        _download_fixed_amount_of_data(response, temp_file, required_length)

    # Does the total number of downloaded bytes match the required length?
    _check_downloaded_length(total_downloaded, required_length,
                             STRICT_REQUIRED_LENGTH=STRICT_REQUIRED_LENGTH,
                             average_download_speed=average_download_speed)

  except Exception:
    # Close 'temp_file'.  Any written data is lost.
    temp_file.close()
    logger.debug('Could not download URL: ' + repr(url))
    raise

  else:
    return temp_file





def _download_fixed_amount_of_data(response, temp_file, required_length):
  """
  <Purpose>
    This is a helper function, where the download really happens. While-block
    reads data from response a fixed chunk of data at a time, or less, until
    'required_length' is reached.

  <Arguments>
    response:
      The object for communicating with the server about the contents of a URL.

    temp_file:
      A temporary file where the contents at the URL specified by the
      'response' object will be stored.

    required_length:
      The number of bytes that we must download for the file.  This is almost
      always specified by the TUF metadata for the data file in question
      (except in the case of timestamp metadata, in which case we would fix a
      reasonable upper bound).

  <Side Effects>
    Data from the server will be written to 'temp_file'.

  <Exceptions>
    tuf.exceptions.SlowRetrievalError
      will be raised if urllib3.exceptions.ReadTimeoutError is caught (if the
      download times out).

    Otherwise, runtime or network exceptions will be raised without question.

  <Returns>
    A (total_downloaded, average_download_speed) tuple, where
    'total_downloaded' is the total number of bytes downloaded for the desired
    file and the 'average_download_speed' calculated for the download
    attempt.
  """

  # Keep track of total bytes downloaded.
  number_of_bytes_received = 0
  average_download_speed = 0

  start_time = timeit.default_timer()

  try:
    while True:
      # We download a fixed chunk of data in every round. This is so that we
      # can defend against slow retrieval attacks. Furthermore, we do not wish
      # to download an extremely large file in one shot.
      # Before beginning the round, sleep (if set) for a short amount of time
      # so that the CPU is not hogged in the while loop.
      if tuf.settings.SLEEP_BEFORE_ROUND:
        time.sleep(tuf.settings.SLEEP_BEFORE_ROUND)

      read_amount = min(
          tuf.settings.CHUNK_SIZE, required_length - number_of_bytes_received)

      # NOTE: This may not handle some servers adding a Content-Encoding
      # header, which may cause urllib3 to misbehave:
      # https://github.com/pypa/pip/blob/404838abcca467648180b358598c597b74d568c9/src/pip/_internal/download.py#L547-L582
      data = response.raw.read(read_amount)

      number_of_bytes_received = number_of_bytes_received + len(data)

      # Data successfully read from the response.  Store it.
      temp_file.write(data)

      if number_of_bytes_received == required_length:
        break

      stop_time = timeit.default_timer()
      seconds_spent_receiving = stop_time - start_time

      # Measure the average download speed.
      average_download_speed = number_of_bytes_received / seconds_spent_receiving

      if average_download_speed < tuf.settings.MIN_AVERAGE_DOWNLOAD_SPEED:
        logger.debug('The average download speed dropped below the minimum'
          ' average download speed set in tuf.settings.py.')
        break

      else:
        logger.debug('The average download speed has not dipped below the'
          ' minimum average download speed set in tuf.settings.py.')

      # We might have no more data to read. Check number of bytes downloaded.
      if not data:
        logger.debug('Downloaded ' + repr(number_of_bytes_received) + '/' +
          repr(required_length) + ' bytes.')

        # Finally, we signal that the download is complete.
        break

  except ReadTimeoutError as e:
    raise tuf.exceptions.SlowRetrievalError(str(e))

  return number_of_bytes_received, average_download_speed



def _check_downloaded_length(total_downloaded, required_length,
                             STRICT_REQUIRED_LENGTH=True,
                             average_download_speed=None):
  """
  <Purpose>
    A helper function which checks whether the total number of downloaded bytes
    matches our expectation.

  <Arguments>
    total_downloaded:
      The total number of bytes supposedly downloaded for the file in question.

    required_length:
      The total number of bytes expected of the file as seen from its metadata.
      The Timestamp role is always downloaded without a known file length, and
      the Root role when the client cannot download any of the required
      top-level roles.  In both cases, 'required_length' is actually an upper
      limit on the length of the downloaded file.

    STRICT_REQUIRED_LENGTH:
      A Boolean indicator used to signal whether we should perform strict
      checking of required_length. True by default. We explicitly set this to
      False when we know that we want to turn this off for downloading the
      timestamp metadata, which has no signed required_length.

    average_download_speed:
     The average download speed for the downloaded file.

  <Side Effects>
    None.

  <Exceptions>
    securesystemslib.exceptions.DownloadLengthMismatchError, if
    STRICT_REQUIRED_LENGTH is True and total_downloaded is not equal
    required_length.

    tuf.exceptions.SlowRetrievalError, if the total downloaded was
    done in less than the acceptable download speed (as set in
    tuf.settings.py).

  <Returns>
    None.
  """

  if total_downloaded == required_length:
    logger.info('Downloaded ' + str(total_downloaded) + ' bytes out of the'
      ' expected ' + str(required_length) + ' bytes.')

  else:
    difference_in_bytes = abs(total_downloaded - required_length)

    # What we downloaded is not equal to the required length, but did we ask
    # for strict checking of required length?
    if STRICT_REQUIRED_LENGTH:
      logger.info('Downloaded ' + str(total_downloaded) + ' bytes, but'
        ' expected ' + str(required_length) + ' bytes. There is a difference'
        ' of ' + str(difference_in_bytes) + ' bytes.')

      # If the average download speed is below a certain threshold, we flag
      # this as a possible slow-retrieval attack.
      logger.debug('Average download speed: ' + repr(average_download_speed))
      logger.debug('Minimum average download speed: ' + repr(tuf.settings.MIN_AVERAGE_DOWNLOAD_SPEED))

      if average_download_speed < tuf.settings.MIN_AVERAGE_DOWNLOAD_SPEED:
        raise tuf.exceptions.SlowRetrievalError(average_download_speed)

      else:
        logger.debug('Good average download speed: ' +
                     repr(average_download_speed) + ' bytes per second')

      raise tuf.exceptions.DownloadLengthMismatchError(required_length, total_downloaded)

    else:
      # We specifically disabled strict checking of required length, but we
      # will log a warning anyway. This is useful when we wish to download the
      # Timestamp or Root metadata, for which we have no signed metadata; so,
      # we must guess a reasonable required_length for it.
      if average_download_speed < tuf.settings.MIN_AVERAGE_DOWNLOAD_SPEED:
        raise tuf.exceptions.SlowRetrievalError(average_download_speed)

      else:
        logger.debug('Good average download speed: ' +
                     repr(average_download_speed) + ' bytes per second')

      logger.info('Downloaded ' + str(total_downloaded) + ' bytes out of an'
        ' upper limit of ' + str(required_length) + ' bytes.')
