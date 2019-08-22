import os
import os.path
import shutil
import stat

from pip._internal.utils.compat import get_path_uid


def check_path_owner(path):
    # type: (str) -> bool
    # If we don't have a way to check the effective uid of this process, then
    # we'll just assume that we own the directory.
    if not hasattr(os, "geteuid"):
        return True

    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Check if path is writable by current user.
            if os.geteuid() == 0:
                # Special handling for root user in order to handle properly
                # cases where users use sudo without -H flag.
                try:
                    path_uid = get_path_uid(path)
                except OSError:
                    return False
                return path_uid == 0
            else:
                return os.access(path, os.W_OK)
        else:
            previous, path = path, os.path.dirname(path)
    return False  # assume we don't own the path


def copy2_fixed(src, dest):
    # type: (str, str) -> None
    """Wrap shutil.copy2() but map errors copying socket files to
    SpecialFileError as expected.

    See also https://bugs.python.org/issue37700.
    """
    try:
        shutil.copy2(src, dest)
    except (OSError, IOError):
        for f in [src, dest]:
            try:
                is_socket_file = is_socket(f)
            except OSError:
                # An error has already occurred. Another error here is not
                # a problem and we can ignore it.
                pass
            else:
                if is_socket_file:
                    raise shutil.SpecialFileError("`%s` is a socket" % f)

        raise


def is_socket(path):
    # type: (str) -> bool
    return stat.S_ISSOCK(os.lstat(path).st_mode)
