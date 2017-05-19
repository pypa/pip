"""Helper for in-memory testing of pip
"""

import contextlib
import io
import sys

import six

import pip


@contextlib.contextmanager
def _replaced_streams(obj, attrs):
    backups = {attr: getattr(obj, attr) for attr in attrs}

    replacements = {}
    for key in backups:
        if six.PY3:
            replacement = io.StringIO()
        else:
            replacement = io.BytesIO()

        setattr(obj, key, replacement)
        replacements[key] = replacement

    try:
        yield replacements
    except:
        raise
    finally:
        for key in backups:
            setattr(sys, key, backups[key])


class InMemoryPipResult(object):

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self._stdout = stdout.getvalue()
        self._stderr = stderr.getvalue()

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def __str__(self):
        raise Exception("Need to use stdout or stderr on InMemoryPip")


class InMemoryPip(object):
    """A TestEnvironment-like object that can be used to test basic commands.
    """

    def pip(self, *args):
        with _replaced_streams(sys, ["stdout", "stderr"]) as replacements:
            try:
                returncode = pip.main(list(args))
            except SystemExit as e:
                returncode = e.code or 0

        return InMemoryPipResult(returncode, **replacements)
