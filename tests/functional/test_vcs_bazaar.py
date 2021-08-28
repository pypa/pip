"""
Contains functional tests of the Bazaar class.
"""

import os
import sys

import pytest

from pip._internal.vcs.bazaar import Bazaar
from pip._internal.vcs.versioncontrol import RemoteNotFoundError
from tests.lib import is_bzr_installed, need_bzr


@pytest.mark.skipif(
    sys.platform == "win32" or "CI" not in os.environ,
    reason="Bazaar is only required under CI",
)
def test_ensure_bzr_available():
    """Make sure that bzr is available when running in CI."""
    assert is_bzr_installed()


@need_bzr
def test_get_remote_url__no_remote(script, tmpdir):
    repo_dir = tmpdir / "temp-repo"
    repo_dir.mkdir()
    repo_dir = str(repo_dir)

    script.run("bzr", "init", repo_dir)

    with pytest.raises(RemoteNotFoundError):
        Bazaar().get_remote_url(repo_dir)
