"""
Contains functional tests of the Bazaar class.
"""

import os

import pytest

from pip._internal.utils.misc import hide_url
from pip._internal.vcs.bazaar import Bazaar
from tests.lib import (
    _test_path_to_file_url,
    _vcs_add,
    create_file,
    is_bzr_installed,
    need_bzr,
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
    source_dir = tmpdir / 'test-source'
    source_dir.mkdir()

    create_file(source_dir / 'test_file', 'something')

    _vcs_add(script, str(source_dir), vcs='bazaar')

    export_dir = str(tmpdir / 'export')
    url = hide_url('bzr+' + _test_path_to_file_url(source_dir))
    Bazaar().export(export_dir, url=url)

    assert os.listdir(export_dir) == ['test_file']


@need_bzr
def test_export_rev(script, tmpdir):
    """Test that a Bazaar branch can be exported, specifying a rev."""
    source_dir = tmpdir / 'test-source'
    source_dir.mkdir()

    # Create a single file that is changed by two revisions.
    create_file(source_dir / 'test_file', 'something initial')
    _vcs_add(script, str(source_dir), vcs='bazaar')

    create_file(source_dir / 'test_file', 'something new')
    script.run(
        'bzr', 'commit', '-q',
        '--author', 'pip <distutils-sig@python.org>',
        '-m', 'change test file', cwd=source_dir,
    )

    export_dir = tmpdir / 'export'
    url = hide_url('bzr+' + _test_path_to_file_url(source_dir) + '@1')
    Bazaar().export(str(export_dir), url=url)

    with open(export_dir / 'test_file', 'r') as f:
        assert f.read() == 'something initial'
