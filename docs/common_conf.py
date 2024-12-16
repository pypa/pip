import os
import re
from typing import Tuple


def read_version() -> Tuple[str, str]:
    # Find the version and release information.
    # We have a single source of truth for our version number: pip's __init__.py file.
    # This next bit of code reads from it.
    file_with_version = os.path.join(
        os.path.dirname(__file__), "..", "src", "pip", "__init__.py"
    )
    with open(file_with_version) as f:
        for line in f:
            m = re.match(r'__version__ = "(.*)"', line)
            if m:
                __version__ = m.group(1)
                # The short X.Y version.
                version = ".".join(__version__.split(".")[:2])
                # The full version, including alpha/beta/rc tags.
                release = __version__
                return version, release
        return "dev", "dev"


# General information about the project.
project = "pip"
copyright = "The pip developers"
version, release = read_version()
