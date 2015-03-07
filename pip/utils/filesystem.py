import os
import os.path

from pip.compat import get_path_uid


def check_path_owner(path):
    # If we don't have a way to check the effective uid of this process, then
    # we'll just assume that we own the directory.
    if not hasattr(os, "geteuid"):
        return True

    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Actually do the ownership check
            try:
                if get_path_uid(path) != os.geteuid():
                    return False
            except OSError:
                return False
            return True
        else:
            previous, path = path, os.path.dirname(path)
