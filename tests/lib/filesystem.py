"""Helpers for filesystem-dependent tests.
"""
import multiprocessing
import os
import socket
import subprocess
import sys
import traceback
from functools import partial
from itertools import chain

from .path import Path


def make_socket_file(path):
    # Socket paths are limited to 108 characters (sometimes less) so we
    # chdir before creating it and use a relative path name.
    cwd = os.getcwd()
    os.chdir(os.path.dirname(path))
    try:
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(os.path.basename(path))
    finally:
        os.chdir(cwd)


def make_unreadable_file(path):
    Path(path).touch()
    os.chmod(path, 0o000)
    if sys.platform == "win32":
        # Once we drop PY2 we can use `os.getlogin()` instead.
        username = os.environ["USERNAME"]
        # Remove "Read Data/List Directory" permission for current user, but
        # leave everything else.
        args = ["icacls", path, "/deny", username + ":(RD)"]
        subprocess.check_call(args)


if sys.platform == 'win32':
    def lock_action(f):
        pass
else:
    def lock_action(f):
        pass


def external_file_opener(conn):
    """
    This external process is run with multiprocessing.
    It waits for a path from the parent, opens it, and then wait for another
     message before closing it.

    :param conn: bi-directional pipe
    :return: nothing
    """
    f = None
    try:
        # Wait for parent to send path
        msg = conn.recv()
        if msg is True:
            # Do nothing - we have been told to exit without a path or action
            pass
        else:
            path, action = msg
            # Open the file
            try:
                f = open(path, 'r')
                # NOTE: action is for future use and may be unused
                if action == 'lock':
                    lock_action(f)
                elif action == 'noread':
                    make_unreadable_file(path)
            # IOError is OSError post PEP 3151
            except OSError:
                traceback.print_exc(None, sys.stderr)
            except IOError:
                traceback.print_exc(None, sys.stderr)

            # Indicate the file is opened
            conn.send(True)
            # Now path is open and we wait for signal to exit
            conn.recv()
    finally:
        if f:
            f.close()
        conn.close()


class FileOpener(object):
    """
    Test class acts as a context manager which can open a file from a
    subprocess, and hold it open to assure that this does not interfere with
    pip's operations.

    If a path is passed to the FileOpener, it immediately sends a message to
    the other process to open that path.  An action of "lock" or "noread" can
    also be sent to the subprocess, resulting in various additional monkey
    wrenches now and in the future.

    Opening the path and taking the action can be deferred however, so that
    the FileOpener may function as a pytest fixture if so desired.
    """
    def __init__(self, path=None, action=None):
        self.path = None
        self.conn, child_conn = multiprocessing.Pipe()
        self.child = multiprocessing.Process(
            target=external_file_opener,
            args=(child_conn,)
        )
        self.child.daemon = True
        self.child.start()
        if path:
            self.send(path, action)

    def send(self, path, action=None):
        if self.path is not None:
            raise AttributeError('path may only be set once')
        self.path = str(path)
        self.conn.send((str(path), action))
        return self.conn.recv()

    def cleanup(self):
        # send a message to the child to exit
        if self.child:
            self.conn.send(True)
            self.child.join()
        self.child = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def get_filelist(base):
    def join(dirpath, dirnames, filenames):
        relative_dirpath = os.path.relpath(dirpath, base)
        join_dirpath = partial(os.path.join, relative_dirpath)
        return chain(
            (join_dirpath(p) for p in dirnames),
            (join_dirpath(p) for p in filenames),
        )

    return set(chain.from_iterable(
        join(*dirinfo) for dirinfo in os.walk(base)
    ))
