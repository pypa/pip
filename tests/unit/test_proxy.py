"""
Tests for the proxy support in pip.
"""

import pip

from tests.lib import SRC_DIR
from tests.lib.path import Path


def test_correct_pip_version():
    """
    Check we are importing pip from the right place.

    """
    assert Path(pip.__file__).folder.folder.abspath == SRC_DIR
