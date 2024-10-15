from pathlib import Path

import pytest

from pip._internal.vcs.subversion import Subversion
from pip._internal.vcs.versioncontrol import RemoteNotFoundError

from tests.lib import PipTestEnvironment, _create_svn_repo, need_svn


@need_svn
def test_get_remote_url__no_remote(script: PipTestEnvironment, tmpdir: Path) -> None:
    repo_path = tmpdir / "temp-repo"
    repo_path.mkdir()
    repo_dir = str(repo_path)

    _create_svn_repo(script.scratch_path, repo_dir)

    with pytest.raises(RemoteNotFoundError):
        Subversion().get_remote_url(repo_dir)


@need_svn
def test_get_remote_url__no_remote_with_setup(
    script: PipTestEnvironment, tmpdir: Path
) -> None:
    repo_path = tmpdir / "temp-repo"
    repo_path.mkdir()
    setup = repo_path / "setup.py"
    setup.touch()
    repo_dir = str(repo_path)

    _create_svn_repo(script.scratch_path, repo_dir)

    with pytest.raises(RemoteNotFoundError):
        Subversion().get_remote_url(repo_dir)
