import contextlib
import os
import sys

_DEBUG = "_ARC_DEBUG" in os.environ

debug_stream = sys.stderr


def debug(*args):
    if _DEBUG:
        print(file=debug_stream, *args)


@contextlib.contextmanager
def mute_stdout():
    stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        yield
    finally:
        sys.stdout = stdout


@contextlib.contextmanager
def mute_stderr():
    stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")
    try:
        yield
    finally:
        sys.stderr.close()
        sys.stderr = stderr


def warn(*args):
    """
    Prints **args** to standard error when running completions. This will interrupt the user's command line interaction;
    use it to indicate an error condition that is preventing your completer from working.
    """
    print(file=debug_stream)
    print(file=debug_stream, *args)
