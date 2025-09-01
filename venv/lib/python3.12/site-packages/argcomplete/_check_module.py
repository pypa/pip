"""
Utility for locating a module (or package's __main__.py) with a given name
and verifying it contains the PYTHON_ARGCOMPLETE_OK marker.

The module name should be specified in a form usable with `python -m`.

Intended to be invoked by argcomplete's global completion function.
"""

import os
import sys
import tokenize
from importlib.util import find_spec


class ArgcompleteMarkerNotFound(RuntimeError):
    pass


def find(name, return_package=False):
    names = name.split(".")
    # Look for the first importlib ModuleSpec that has `origin` set, indicating it's not a namespace package.
    for package_name_boundary in range(len(names)):
        spec = find_spec(".".join(names[: package_name_boundary + 1]))
        if spec is not None and spec.origin is not None:
            break

    if spec is None:
        raise ArgcompleteMarkerNotFound('no module named "{}"'.format(names[0]))
    if not spec.has_location:
        raise ArgcompleteMarkerNotFound("cannot locate file")
    if spec.submodule_search_locations is None:
        if len(names) != 1:
            raise ArgcompleteMarkerNotFound("{} is not a package".format(names[0]))
        return spec.origin
    if len(spec.submodule_search_locations) != 1:
        raise ArgcompleteMarkerNotFound("expecting one search location")
    path = os.path.join(spec.submodule_search_locations[0], *names[package_name_boundary + 1 :])
    if os.path.isdir(path):
        filename = "__main__.py"
        if return_package:
            filename = "__init__.py"
        return os.path.join(path, filename)
    else:
        return path + ".py"


def main():
    try:
        name = sys.argv[1]
    except IndexError:
        raise ArgcompleteMarkerNotFound("missing argument on the command line")

    filename = find(name)

    try:
        fp = tokenize.open(filename)
    except OSError:
        raise ArgcompleteMarkerNotFound("cannot open file")

    with fp:
        head = fp.read(1024)

    if "PYTHON_ARGCOMPLETE_OK" not in head:
        raise ArgcompleteMarkerNotFound("marker not found")


if __name__ == "__main__":
    try:
        main()
    except ArgcompleteMarkerNotFound as e:
        sys.exit(str(e))
