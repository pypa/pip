"""
Utility for locating the module (or package's __init__.py)
associated with a given console_script name
and verifying it contains the PYTHON_ARGCOMPLETE_OK marker.

Such scripts are automatically generated and cannot contain
the marker themselves, so we defer to the containing module or package.

For more information on setuptools console_scripts, see
https://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation

Intended to be invoked by argcomplete's global completion function.
"""

import os
import sys
from importlib.metadata import EntryPoint
from importlib.metadata import entry_points as importlib_entry_points
from typing import Iterable

from ._check_module import ArgcompleteMarkerNotFound, find


def main():
    # Argument is the full path to the console script.
    script_path = sys.argv[1]

    # Find the module and function names that correspond to this
    # assuming it is actually a console script.
    name = os.path.basename(script_path)

    entry_points: Iterable[EntryPoint] = importlib_entry_points()  # type:ignore

    # Python 3.12+ returns a tuple of entry point objects
    # whereas <=3.11 returns a SelectableGroups object
    if sys.version_info < (3, 12):
        entry_points = entry_points["console_scripts"]  # type:ignore

    entry_points = [ep for ep in entry_points if ep.name == name and ep.group == "console_scripts"]  # type:ignore

    if not entry_points:
        raise ArgcompleteMarkerNotFound("no entry point found matching script")
    entry_point = entry_points[0]
    module_name, function_name = entry_point.value.split(":", 1)

    # Check this looks like the script we really expected.
    with open(script_path) as f:
        script = f.read()
    if "from {} import {}".format(module_name, function_name) not in script:
        raise ArgcompleteMarkerNotFound("does not appear to be a console script")
    if "sys.exit({}())".format(function_name) not in script:
        raise ArgcompleteMarkerNotFound("does not appear to be a console script")

    # Look for the argcomplete marker in the script it imports.
    with open(find(module_name, return_package=True)) as f:
        head = f.read(1024)
    if "PYTHON_ARGCOMPLETE_OK" not in head:
        raise ArgcompleteMarkerNotFound("marker not found")


if __name__ == "__main__":
    try:
        main()
    except ArgcompleteMarkerNotFound as e:
        sys.exit(str(e))
