#!/usr/bin/env python
"""
<Program Name>
  process.py

<Author>
  Trishank Karthik Kuppusamy <trishank.kuppusamy@datadoghq.com>
  Lukas Puehringer <lukas.puehringer@nyu.edu>

<Started>
  September 25, 2018

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Provide a common interface for Python's subprocess module to:

  - require the Py3 subprocess backport `subprocess32` on Python2,
  - namespace subprocess constants (DEVNULL, PIPE) and
  - provide a custom `subprocess.run` wrapper
  - provide a special `run_duplicate_streams` function

"""
import os
import sys
import io
import tempfile
import logging
import time
import shlex
from pip._vendor import six

if six.PY2:
  import subprocess32 as subprocess # pragma: no cover pylint: disable=import-error
else: # pragma: no cover
  import subprocess

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import settings as _securesystemslib_settings
securesystemslib.settings = _securesystemslib_settings

DEVNULL = subprocess.DEVNULL
PIPE = subprocess.PIPE

log = logging.getLogger(__name__)

def _default_timeout():
  """Helper to use securesystemslib.settings.SUBPROCESS_TIMEOUT as default
  argument, and still be able to modify it after the function definitions are
  evaluated. """
  return securesystemslib.settings.SUBPROCESS_TIMEOUT



def run(cmd, check=True, timeout=_default_timeout(), **kwargs):
  """
  <Purpose>
    Provide wrapper for `subprocess.run` (see
    https://github.com/python/cpython/blob/3.5/Lib/subprocess.py#L352-L399)
    where:

    * `timeout` has a default (securesystemslib.settings.SUBPROCESS_TIMEOUT),
    * `check` is `True` by default,
    * there is only one positional argument, i.e. `cmd` that can be either
      a str (will be split with shlex) or a list of str and
    * instead of raising a ValueError if both `input` and `stdin` are passed,
      `stdin` is ignored.


  <Arguments>
    cmd:
            The command and its arguments. (list of str, or str)
            Splits a string specifying a command and its argument into a list
            of substrings, if necessary.

    check: (default True)
            "If check is true, and the process exits with a non-zero exit code,
            a CalledProcessError exception will be raised. Attributes of that
            exception hold the arguments, the exit code, and stdout and stderr
            if they were captured."

    timeout: (default see securesystemslib.settings.SUBPROCESS_TIMEOUT)
            "The timeout argument is passed to Popen.communicate(). If the
            timeout expires, the child process will be killed and waited for.
            The TimeoutExpired exception will be re-raised after the child
            process has terminated."

    **kwargs:
            See subprocess.run and Frequently Used Arguments to Popen
            constructor for available kwargs.
            https://docs.python.org/3.5/library/subprocess.html#subprocess.run
            https://docs.python.org/3.5/library/subprocess.html#frequently-used-arguments

  <Exceptions>
    securesystemslib.exceptions.FormatError:
            If the `cmd` is a list and does not match
            securesystemslib.formats.LIST_OF_ANY_STRING_SCHEMA.

    OSError:
            If the given command is not present or non-executable.

    subprocess.TimeoutExpired:
            If the process does not terminate after timeout seconds. Default
            is `settings.SUBPROCESS_TIMEOUT`

  <Side Effects>
    The side effects of executing the given command in this environment.

  <Returns>
    A subprocess.CompletedProcess instance.

  """
  # Make list of command passed as string for convenience
  if isinstance(cmd, six.string_types):
    cmd = shlex.split(cmd)
  else:
    securesystemslib.formats.LIST_OF_ANY_STRING_SCHEMA.check_match(cmd)

  # NOTE: The CPython implementation would raise a ValueError here, we just
  # don't pass on `stdin` if the user passes `input` and `stdin`
  # https://github.com/python/cpython/blob/3.5/Lib/subprocess.py#L378-L381
  if kwargs.get("input") is not None and "stdin" in kwargs:
    log.debug("stdin and input arguments may not both be used. "
        "Ignoring passed stdin: " + str(kwargs["stdin"]))
    del kwargs["stdin"]

  return subprocess.run(cmd, check=check, timeout=timeout, **kwargs)




def run_duplicate_streams(cmd, timeout=_default_timeout()):
  """
  <Purpose>
    Provide a function that executes a command in a subprocess and, upon
    termination, returns its exit code and the contents of what was printed to
    its standard streams.

    * Might behave unexpectedly with interactive commands.
    * Might not duplicate output in real time, if the command buffers it (see
      e.g. `print("foo")` vs. `print("foo", flush=True)` in Python 3).

  <Arguments>
    cmd:
            The command and its arguments. (list of str, or str)
            Splits a string specifying a command and its argument into a list
            of substrings, if necessary.

    timeout: (default see settings.SUBPROCESS_TIMEOUT)
            If the timeout expires, the child process will be killed and waited
            for and then subprocess.TimeoutExpired will be raised.

  <Exceptions>
    securesystemslib.exceptions.FormatError:
            If the `cmd` is a list and does not match
            securesystemslib.formats.LIST_OF_ANY_STRING_SCHEMA.

    OSError:
            If the given command is not present or non-executable.

    subprocess.TimeoutExpired:
            If the process does not terminate after timeout seconds. Default
            is `settings.SUBPROCESS_TIMEOUT`

  <Side Effects>
    The side effects of executing the given command in this environment.

  <Returns>
    A tuple of command's exit code, standard output and standard error
    contents.

  """
  if isinstance(cmd, six.string_types):
    cmd = shlex.split(cmd)
  else:
    securesystemslib.formats.LIST_OF_ANY_STRING_SCHEMA.check_match(cmd)

  # Use temporary files as targets for child process standard stream redirects
  # They seem to work better (i.e. do not hang) than pipes, when using
  # interactive commands like `vi`.
  stdout_fd, stdout_name = tempfile.mkstemp()
  stderr_fd, stderr_name = tempfile.mkstemp()
  try:
    with io.open(stdout_name, "r") as stdout_reader, \
        os.fdopen(stdout_fd, "w") as stdout_writer, \
        io.open(stderr_name, "r") as stderr_reader, \
        os.fdopen(stderr_fd, "w") as stderr_writer:

      # Store stream results in mutable dict to update it inside nested helper
      _std = {"out": "", "err": ""}
      def _duplicate_streams():
        """Helper to read from child process standard streams, write their
        contents to parent process standard streams, and build up return values
        for outer function.
        """
        # Read until EOF but at most `io.DEFAULT_BUFFER_SIZE` bytes per call.
        # Reading and writing in reasonably sized chunks prevents us from
        # subverting a timeout, due to being busy for too long or indefinitely.
        stdout_part = stdout_reader.read(io.DEFAULT_BUFFER_SIZE)
        stderr_part = stderr_reader.read(io.DEFAULT_BUFFER_SIZE)
        sys.stdout.write(stdout_part)
        sys.stderr.write(stderr_part)
        sys.stdout.flush()
        sys.stderr.flush()
        _std["out"] += stdout_part
        _std["err"] += stderr_part

      # Start child process, writing its standard streams to temporary files
      proc = subprocess.Popen(cmd, stdout=stdout_writer,
          stderr=stderr_writer, universal_newlines=True)
      proc_start_time = time.time()

      # Duplicate streams until the process exits (or times out)
      while proc.poll() is None:
        # Time out as Python's `subprocess` would do it
        if (timeout is not None and
            time.time() > proc_start_time + timeout):
          proc.kill()
          proc.wait()
          raise subprocess.TimeoutExpired(cmd, timeout)

        _duplicate_streams()

      # Read/write once more to grab everything that the process wrote between
      # our last read in the loop and exiting, i.e. breaking the loop.
      _duplicate_streams()

  finally:
    # The work is done or was interrupted, the temp files can be removed
    os.remove(stdout_name)
    os.remove(stderr_name)

  # Return process exit code and captured streams
  return proc.poll(), _std["out"], _std["err"]
