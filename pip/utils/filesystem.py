import os
import os.path


def check_path_owner(path):
    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Check if path is writable
            return os.access(path, os.W_OK)
        else:
            previous, path = path, os.path.dirname(path)
