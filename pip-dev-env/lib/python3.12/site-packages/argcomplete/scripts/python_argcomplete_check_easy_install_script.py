#!/usr/bin/env python3

# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

"""
This script is part of the Python argcomplete package (https://github.com/kislyuk/argcomplete).
It is used to check if an EASY-INSTALL-SCRIPT wrapper redirects to a script that contains the string
"PYTHON_ARGCOMPLETE_OK". If you have enabled global completion in argcomplete, the completion hook will run it every
time you press <TAB> in your shell.

Usage:
    python-argcomplete-check-easy-install-script <input executable file>
"""

import sys

# PEP 366
__package__ = "argcomplete.scripts"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    sys.tracebacklimit = 0

    with open(sys.argv[1]) as fh:
        line1, head = fh.read(1024).split("\n", 1)[:2]
        if line1.startswith("#") and ("py" in line1 or "Py" in line1):
            import re

            lines = head.split("\n", 12)
            for line in lines:
                if line.startswith("# EASY-INSTALL-SCRIPT"):
                    import pkg_resources  # type: ignore

                    re_match = re.match("# EASY-INSTALL-SCRIPT: '(.+)','(.+)'", line)
                    assert re_match is not None
                    dist, script = re_match.groups()
                    if "PYTHON_ARGCOMPLETE_OK" in pkg_resources.get_distribution(dist).get_metadata(
                        "scripts/" + script
                    ):
                        return 0
                elif line.startswith("# EASY-INSTALL-ENTRY-SCRIPT"):
                    re_match = re.match("# EASY-INSTALL-ENTRY-SCRIPT: '(.+)','(.+)','(.+)'", line)
                    assert re_match is not None
                    dist, group, name = re_match.groups()
                    import pkgutil

                    import pkg_resources  # type: ignore

                    entry_point_info = pkg_resources.get_distribution(dist).get_entry_info(group, name)
                    assert entry_point_info is not None
                    module_name = entry_point_info.module_name
                    with open(pkgutil.get_loader(module_name).get_filename()) as mod_fh:  # type: ignore
                        if "PYTHON_ARGCOMPLETE_OK" in mod_fh.read(1024):
                            return 0
                elif line.startswith("# EASY-INSTALL-DEV-SCRIPT"):
                    for line2 in lines:
                        if line2.startswith("__file__"):
                            re_match = re.match("__file__ = '(.+)'", line2)
                            assert re_match is not None
                            filename = re_match.group(1)
                            with open(filename) as mod_fh:
                                if "PYTHON_ARGCOMPLETE_OK" in mod_fh.read(1024):
                                    return 0
                elif line.startswith("# PBR Generated"):
                    re_match = re.search("from (.*) import", head)
                    assert re_match is not None
                    module = re_match.groups()[0]
                    import pkgutil

                    import pkg_resources  # type: ignore

                    with open(pkgutil.get_loader(module).get_filename()) as mod_fh:  # type: ignore
                        if "PYTHON_ARGCOMPLETE_OK" in mod_fh.read(1024):
                            return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
