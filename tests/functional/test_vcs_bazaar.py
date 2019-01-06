"""
Contains functional tests of the Bazaar class.
"""

import os

from pip._internal.vcs.bazaar import Bazaar
from tests.lib import _test_path_to_file_url, _vcs_add, create_file, need_bzr


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
