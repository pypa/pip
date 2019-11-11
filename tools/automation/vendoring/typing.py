"""Logic for adding static typing related stubs of vendored dependencies.

We autogenerate `.pyi` stub files for the vendored modules, when vendoring.
These .pyi files are not distributed (thanks to MANIFEST.in). The stub files
are merely `from ... import *` but they do what they're supposed to and mypy
is able to find the correct declarations using these files.
"""

import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

EXTRA_STUBS_NEEDED = {
    # Some projects need stubs other than a simple <name>.pyi
    "six": [
        "six.__init__",
        "six.moves.__init__",
        "six.moves.configparser",
    ],
    # Some projects should not have stubs because they're a single module
    "appdirs": [],
    "contextlib2": [],
}  # type: Dict[str, List[str]]


def determine_stub_files(lib):
    # type: (str) -> Iterable[Tuple[str, str]]
    # There's no special handling needed -- a <libname>.pyi file is good enough
    if lib not in EXTRA_STUBS_NEEDED:
        yield lib + ".pyi", lib
        return

    # Need to generate the given stubs, with the correct import names
    for import_name in EXTRA_STUBS_NEEDED[lib]:
        rel_location = import_name.replace(".", os.sep) + ".pyi"

        # Writing an __init__.pyi file -> don't import from `pkg.__init__`
        if import_name.endswith(".__init__"):
            import_name = import_name[:-9]

        yield rel_location, import_name


def write_stub(destination, import_name):
    # type: (Path, str) -> None
    # Create the parent directories if needed.
    if not destination.parent.exists():
        destination.parent.mkdir()

    # Write `from ... import *` in the stub file.
    destination.write_text("from %s import *" % import_name)


def generate_stubs(vendor_dir, libraries):
    # type: (Path, List[str]) -> None
    for lib in libraries:
        for rel_location, import_name in determine_stub_files(lib):
            destination = vendor_dir / rel_location
            write_stub(destination, import_name)
