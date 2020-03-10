# flake8: noqa
# -*- coding: utf-8 -*-
# Author: Aziz Köksal
from __future__ import absolute_import

import glob
import os
import shutil

from pip._vendor import six

try:
    from os import supports_fd
except ImportError:
    supports_fd = set()



_base = six.text_type if os.path.supports_unicode_filenames else str


class Path(_base):
    """
    Models a path in an object oriented way.
    """

    # File system path separator: '/' or '\'.
    sep = os.sep

    # Separator in the PATH environment variable.
    pathsep = os.pathsep

    def __new__(cls, *paths):
        if len(paths):
            return _base.__new__(cls, os.path.join(*paths))
        return _base.__new__(cls)

    def __div__(self, path):
        """
        Joins this path with another path.

        >>> path_obj / 'bc.d'
        >>> path_obj / path_obj2
        """
        return Path(self, path)

    __truediv__ = __div__

    def __rdiv__(self, path):
        """
        Joins this path with another path.

        >>> "/home/a" / path_obj
        """
        return Path(path, self)

    __rtruediv__ = __rdiv__

    def __idiv__(self, path):
        """
        Like __div__ but also assigns to the variable.

        >>> path_obj /= 'bc.d'
        """
        return Path(self, path)

    __itruediv__ = __idiv__

    def __add__(self, path):
        """
        >>> Path('/home/a') + 'bc.d'
        '/home/abc.d'
        """
        return Path(_base(self) + path)

    def __radd__(self, path):
        """
        >>> '/home/a' + Path('bc.d')
        '/home/abc.d'
        """
        return Path(path + _base(self))

    def __repr__(self):
        return u"Path({inner})".format(inner=_base.__repr__(self))

    def __hash__(self):
        return _base.__hash__(self)

    @property
    def name(self):
        """
        '/home/a/bc.d' -> 'bc.d'
        """
        return os.path.basename(self)

    @property
    def stem(self):
        """
        '/home/a/bc.d' -> 'bc'
        """
        return Path(os.path.splitext(self)[0]).name

    @property
    def suffix(self):
        """
        '/home/a/bc.d' -> '.d'
        """
        return Path(os.path.splitext(self)[1])

    def resolve(self):
        """
        Resolves symbolic links.
        """
        return Path(os.path.realpath(self))

    @property
    def parent(self):
        """
        Returns the parent directory of this path.

        '/home/a/bc.d' -> '/home/a'
        '/home/a/' -> '/home/a'
        '/home/a' -> '/home'
        """
        return Path(os.path.dirname(self))

    def exists(self):
        """
        Returns True if the path exists.
        """
        return os.path.exists(self)

    def mkdir(self, mode=0x1FF, exist_ok=False, parents=False):  # 0o777
        """
        Creates a directory, if it doesn't exist already.

        :param parents: Whether to create parent directories.
        """

        maker_func = os.makedirs if parents else os.mkdir
        try:
            maker_func(self, mode)
        except OSError:
            if not exist_ok or not os.path.isdir(self):
                raise

    def unlink(self):
        """
        Removes a file.
        """
        return os.remove(self)

    def rmdir(self):
        """
        Removes a directory.
        """
        return os.rmdir(self)

    def rename(self, to):
        """
        Renames a file or directory. May throw an OSError.
        """
        return os.rename(self, to)

    def glob(self, pattern):
        return (Path(i) for i in glob.iglob(self.joinpath(pattern)))

    def joinpath(self, *parts):
        return Path(self, *parts)

    # TODO: Remove after removing inheritance from str.
    def join(self, *parts):
        raise RuntimeError('Path.join is invalid, use joinpath instead.')

    def read_bytes(self):
        # type: () -> bytes
        with open(self, "rb") as fp:
            return fp.read()

    def write_bytes(self, content):
        # type: (bytes) -> None
        with open(self, "wb") as f:
            f.write(content)

    def read_text(self):
        with open(self, "r") as fp:
            return fp.read()

    def write_text(self, content):
        with open(self, "w") as fp:
            fp.write(content)

    def touch(self):
        with open(self, "a") as fp:
            path = fp.fileno() if os.utime in supports_fd else self
            os.utime(path, None)  # times is not optional on Python 2.7

    def symlink_to(self, target):
        os.symlink(target, self)

    def stat(self):
        return os.stat(self)

curdir = Path(os.path.curdir)
