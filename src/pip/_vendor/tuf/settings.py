#!/usr/bin/env python

# Copyright 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  settings.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  January 11, 2017

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
 A central location for TUF configuration settings.  Example options include
 setting the destination of temporary files and downloaded content, the maximum
 length of downloaded metadata (unknown file attributes), and download
 behavior.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


# Set a directory that should be used for all temporary files. If this
# is None, then the system default will be used. The system default
# will also be used if a directory path set here is invalid or
# unusable.
temporary_directory = None

# Set a local directory to store metadata that is requested from mirrors.  This
# directory contains subdirectories for different repositories, where each
# subdirectory contains a different set of metadata.  For example:
# tuf.settings.repositories_directory = /tmp/repositories.  The root file for a
# repository named 'django_repo' can be found at:
# /tmp/repositories/django_repo/metadata/current/root.METADATA_EXTENSION
repositories_directory = None

# The 'log.py' module manages TUF's logging system.  Users have the option to
# enable/disable logging to a file via 'ENABLE_FILE_LOGGING', or
# tuf.log.enable_file_logging() and tuf.log.disable_file_logging().
ENABLE_FILE_LOGGING = False

# If file logging is enabled via 'ENABLE_FILE_LOGGING', TUF log messages will
# be saved to 'LOG_FILENAME'
LOG_FILENAME = 'tuf.log'

# Since the timestamp role does not have signed metadata about itself, we set a
# default but sane upper bound for the number of bytes required to download it.
DEFAULT_TIMESTAMP_REQUIRED_LENGTH = 16384 #bytes

# The Root role may be updated without knowing its version if top-level
# metadata cannot be safely downloaded (e.g., keys may have been revoked, thus
# requiring a new Root file that includes the updated keys).  Set a default
# upper bound for the maximum total bytes that may be downloaded for Root
# metadata.
DEFAULT_ROOT_REQUIRED_LENGTH = 512000 #bytes

# Set a default, but sane, upper bound for the number of bytes required to
# download Snapshot metadata.
DEFAULT_SNAPSHOT_REQUIRED_LENGTH = 2000000 #bytes

# Set a default, but sane, upper bound for the number of bytes required to
# download Targets metadata.
DEFAULT_TARGETS_REQUIRED_LENGTH = 5000000 #bytes

# Set a timeout value in seconds (float) for non-blocking socket operations.
SOCKET_TIMEOUT = 4 #seconds

# The maximum chunk of data, in bytes, we would download in every round.
CHUNK_SIZE = 400000 #bytes

# The minimum average download speed (bytes/second) that must be met to
# avoid being considered as a slow retrieval attack.
MIN_AVERAGE_DOWNLOAD_SPEED = 50 #bytes/second

# By default, limit number of delegatees we visit for any target.
MAX_NUMBER_OF_DELEGATIONS = 2**5

# A setting for the instances where a default hashing algorithm is needed.
# This setting is currently used to calculate the path hash prefixes of hashed
# bin delegations, and digests of targets filepaths.  The other instances
# (e.g., digest of files) that require a hashing algorithm rely on settings in
# the securesystemslib external library.
DEFAULT_HASH_ALGORITHM = 'sha256'

# The hashing algorithms used to compute file hashes
FILE_HASH_ALGORITHMS = ['sha256', 'sha512']

# The client's update procedure (contained within a while-loop) can potentially
# hog the CPU.  The following setting can be used to force the update sequence
# to suspend execution for a specified amount of time.  See
# theupdateframework/tuf/issue#338.
SLEEP_BEFORE_ROUND = None

# Maximum number of root metadata file rotations we should perform in order to
# prevent a denial-of-service (DoS) attack.
MAX_NUMBER_ROOT_ROTATIONS = 2**5
