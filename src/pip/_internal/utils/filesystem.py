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


def copytree(*args, **kwargs):
    """Wrap shutil.copytree() to map errors copying socket file to
    SpecialFileError.

    See also https://bugs.python.org/issue37700.
    """
    def to_correct_error(src, dest, error):
        for f in [src, dest]:
            try:
                if is_socket(f):
                    new_error = shutil.SpecialFileError("`%s` is a socket" % f)
                    return (src, dest, new_error)
            except OSError:
                # An error has already occurred. Another error here is not
                # a problem and we can ignore it.
                pass

        return (src, dest, error)

    try:
        shutil.copytree(*args, **kwargs)
    except shutil.Error as e:
        errors = e.args[0]
        new_errors = [
            to_correct_error(src, dest, error) for src, dest, error in errors
        ]
        raise shutil.Error(new_errors)


def is_socket(path):
    # type: (str) -> bool
    return stat.S_ISSOCK(os.lstat(path).st_mode)
