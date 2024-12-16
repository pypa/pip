import glob
import os
import sys
from typing import List, Tuple

# Add the docs/ directory to sys.path to load the common config
docs_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, docs_dir)

from common_conf import copyright, project, release, version  # noqa: E402, F401

extensions = [
    # our extensions
    "pip_sphinxext",
]

print("pip version:", version)
print("pip release:", release)


# List of manual pages generated
def determine_man_pages() -> List[Tuple[str, str, str, str, int]]:
    """Determine which man pages need to be generated."""

    def to_document_name(path: str, base_dir: str) -> str:
        """Convert a provided path to a Sphinx "document name"."""
        relative_path = os.path.relpath(path, base_dir)
        root, _ = os.path.splitext(relative_path)
        return root.replace(os.sep, "/")

    # Crawl the entire man/commands/ directory and list every file with appropriate
    # name and details.
    man_dir = os.path.join(docs_dir, "man")
    raw_subcommands = glob.glob(os.path.join(man_dir, "commands/*.rst"))
    if not raw_subcommands:
        raise FileNotFoundError(
            "The individual subcommand manpages could not be found!"
        )

    retval = [
        ("index", "pip", "package manager for Python packages", "pip developers", 1),
    ]
    for fname in raw_subcommands:
        fname_base = to_document_name(fname, man_dir)
        outname = "pip-" + fname_base.split("/")[1]
        description = "description of {} command".format(outname.replace("-", " "))

        retval.append((fname_base, outname, description, "pip developers", 1))

    return retval


man_pages = determine_man_pages()
