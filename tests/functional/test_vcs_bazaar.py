"""
Contains functional tests of the Bazaar class.
"""

import os

import pytest

from pip._internal.vcs.bazaar import Bazaar
from tests.lib import (
    _test_path_to_file_url, _vcs_add, create_file, is_bzr_installed, need_bzr,
)


@pytest.mark.skipif(
    'TRAVIS' not in os.environ,
    reason='Bazaar is only required under Travis')
def test_ensure_bzr_available():
    """Make sure that bzr is available when running in Travis."""
    assert is_bzr_installed()


@need_bzr
def test_export(script, tmpdir):
    """Test that a Bazaar branch can be exported."""
    branch_path = tmpdir / 'test-branch'
    branch_path.mkdir()

    create_file(branch_path / 'test_file', 'something')

    _vcs_add(script, str(branch_path), vcs='bazaar')

    bzr = Bazaar('bzr+' + _test_path_to_file_url(branch_path))
    export_dir = str(tmpdir / 'export')
    bzr.export(export_dir)

    assert os.listdir(export_dir) == ['test_file']
