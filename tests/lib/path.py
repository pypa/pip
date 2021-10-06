# Author: Aziz Köksal
import glob
import os
from typing import Iterable, Iterator, Union


class Path(str):
    """
    Models a path in an object oriented way.
    """

    # File system path separator: '/' or '\'.
    sep = os.sep

    # Separator in the PATH environment variable.
    pathsep = os.pathsep

    def __new__(cls, *paths: str) -> "Path":
        if len(paths):
            return super().__new__(cls, os.path.join(*paths))
        return super().__new__(cls)

    def __div__(self, path: str) -> "Path":
        """
        Joins this path with another path.

        >>> path_obj / 'bc.d'
        >>> path_obj / path_obj2
        """
        return Path(self, path)

    __truediv__ = __div__

    def __rdiv__(self, path: str) -> "Path":
        """
        Joins this path with another path.

        >>> "/home/a" / path_obj
        """
        return Path(path, self)

    __rtruediv__ = __rdiv__

    def __idiv__(self, path: str) -> "Path":
        """
        Like __div__ but also assigns to the variable.

        >>> path_obj /= 'bc.d'
        """
        return Path(self, path)

    __itruediv__ = __idiv__

    def __add__(self, path: str) -> "Path":
        """
        >>> Path('/home/a') + 'bc.d'
        '/home/abc.d'
        """
        return Path(str(self) + path)

    def __radd__(self, path: str) -> "Path":
        """
        >>> '/home/a' + Path('bc.d')
        '/home/abc.d'
        """
        return Path(path + str(self))

    def __repr__(self) -> str:
        return "Path({inner})".format(inner=str.__repr__(self))

    @property
    def name(self) -> str:
        """
        '/home/a/bc.d' -> 'bc.d'
        """
        return os.path.basename(self)

    @property
    def stem(self) -> str:
        """
        '/home/a/bc.d' -> 'bc'
        """
        return Path(os.path.splitext(self)[0]).name

    @property
    def suffix(self) -> str:
        """
        '/home/a/bc.d' -> '.d'
        """
        return Path(os.path.splitext(self)[1])

    def resolve(self) -> "Path":
        """
        Resolves symbolic links.
        """
        return Path(os.path.realpath(self))

    @property
    def parent(self) -> "Path":
        """
        Returns the parent directory of this path.

        '/home/a/bc.d' -> '/home/a'
        '/home/a/' -> '/home/a'
        '/home/a' -> '/home'
        """
        return Path(os.path.dirname(self))

    def exists(self) -> bool:
        """
        Returns True if the path exists.
        """
        return os.path.exists(self)

    def mkdir(
        self,
        mode: int = 0o777,
        exist_ok: bool = False,
        parents: bool = False,
    ) -> None:
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

    def unlink(self) -> None:
        """
        Removes a file.
        """
        os.remove(self)

    def rmdir(self) -> None:
        """
        Removes a directory.
        """
        os.rmdir(self)

    def rename(self, to: str) -> None:
        """
        Renames a file or directory. May throw an OSError.
        """
        os.rename(self, to)

    def glob(self, pattern: str) -> Iterator["Path"]:
        return (Path(i) for i in glob.iglob(self.joinpath(pattern)))

    def joinpath(self, *parts: str) -> "Path":
        return Path(self, *parts)

    # TODO: Remove after removing inheritance from str.
    def join(self, parts: Iterable[str]) -> str:
        raise RuntimeError("Path.join is invalid, use joinpath instead.")

    def read_bytes(self) -> bytes:
        with open(self, "rb") as fp:
            return fp.read()

    def write_bytes(self, content: bytes) -> None:
        with open(self, "wb") as f:
            f.write(content)

    def read_text(self) -> str:
        with open(self, "r") as fp:
            return fp.read()

    def write_text(self, content: str) -> None:
        with open(self, "w") as fp:
            fp.write(content)

    def touch(self) -> None:
        with open(self, "a") as fp:
            path: Union[int, str] = fp.fileno() if os.utime in os.supports_fd else self
            os.utime(path)

    def symlink_to(self, target: str) -> None:
        os.symlink(target, self)

    def stat(self) -> os.stat_result:
        return os.stat(self)


curdir = Path(os.path.curdir)
