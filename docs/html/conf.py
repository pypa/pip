"""Sphinx configuration file for pip's documentation."""

import os
import pathlib
import sys

# Add the docs/ directory to sys.path to load the common config,
# and pip_sphinxext.py
docs_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, docs_dir)

from common_conf import copyright, project, release, version  # noqa: E402, F401

# -- General configuration ------------------------------------------------------------

extensions = [
    # first-party extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    # our extensions
    "pip_sphinxext",
    # third-party extensions
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinxcontrib.towncrier",
]

print("pip version:", version)
print("pip release:", release)

# -- Options for myst-parser ----------------------------------------------------------

myst_enable_extensions = ["deflist"]
myst_heading_anchors = 3

# -- Options for smartquotes ----------------------------------------------------------

# Disable the conversion of dashes so that long options like "--find-links" won't
# render as "-find-links" if included in the text.The default of "qDe" converts normal
# quote characters ('"' and "'"), en and em dashes ("--" and "---"), and ellipses "..."
smartquotes_action = "qe"

# -- Options for intersphinx ----------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pypug": ("https://packaging.python.org", None),
}

# -- Options for extlinks -------------------------------------------------------------

extlinks = {
    "issue": ("https://github.com/pypa/pip/issues/%s", "#%s"),
    "pull": ("https://github.com/pypa/pip/pull/%s", "PR #%s"),
    "pypi": ("https://pypi.org/project/%s/", "%s"),
}

# -- Options for towncrier_draft extension --------------------------------------------

towncrier_draft_autoversion_mode = "draft"  # or: 'sphinx-release', 'sphinx-version'
towncrier_draft_include_empty = True
towncrier_draft_working_directory = pathlib.Path(docs_dir).parent
# Not yet supported: towncrier_draft_config_path = 'pyproject.toml'  # relative to cwd

# -- Options for HTML -----------------------------------------------------------------

html_theme = "furo"
html_title = f"{project} documentation v{release}"

# Disable the generation of the various indexes
html_use_modindex = False
html_use_index = False

# -- Options for sphinx_copybutton ----------------------------------------------------

copybutton_prompt_text = r"\$ | C\:\> "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = False
