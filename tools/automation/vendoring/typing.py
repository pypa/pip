"""Logic for adding static typing related stubs of vendored dependencies.

We autogenerate `.pyi` stub files for the vendored modules, when vendoring.
These .pyi files are not distributed (thanks to MANIFEST.in). The stub files
are merely `from ... import *` but they do what they're supposed to and mypy
is able to find the correct declarations using these files.
"""

import os

extra_stubs_needed = {
    # Some projects need stubs other than a simple <name>.pyi
    "six": [
        "six.__init__",
        "six.moves.__init__",
        "six.moves.configparser",
    ],
    # Some projects should not have stubs coz they're single file modules
    "appdirs": [],
    "contextlib2": [],
}


def generate_stubs(vendor_dir, vendored_libs):
    for lib in vendored_libs:
        if lib not in extra_stubs_needed:
            (vendor_dir / (lib + ".pyi")).write_text("from %s import *" % lib)
            continue

        for selector in extra_stubs_needed[lib]:
            fname = selector.replace(".", os.sep) + ".pyi"
            if selector.endswith(".__init__"):
                selector = selector[:-9]

            f_path = vendor_dir / fname
            if not f_path.parent.exists():
                f_path.parent.mkdir()
            f_path.write_text("from %s import *" % selector)
