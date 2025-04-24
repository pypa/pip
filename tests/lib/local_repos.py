import os
import subprocess
import urllib.request
from pathlib import Path

from pip._internal.utils.misc import hide_url
from pip._internal.vcs import vcs


def _create_svn_initools_repo(initools_dir: str) -> None:
    """
    Create the SVN INITools repo.
    """
    directory = os.path.dirname(initools_dir)
    subprocess.check_call("svnadmin create INITools".split(), cwd=directory)

    filename, _ = urllib.request.urlretrieve(
        "http://bitbucket.org/hltbra/pip-initools-dump/raw/8b55c908a320/"
        "INITools_modified.dump"
    )
    with open(filename) as dump:
        subprocess.check_call(
            ["svnadmin", "load", initools_dir],
            stdin=dump,
            stdout=subprocess.DEVNULL,
        )
    os.remove(filename)


def local_checkout(
    remote_repo: str,
    temp_path: Path,
) -> str:
    """
    :param temp_path: the return value of the tmpdir fixture, which is a
        temp directory Path object unique to each test function invocation,
        created as a sub directory of the base temp directory.
    """
    assert "+" in remote_repo
    vcs_name, vcs_url = remote_repo.split("+", 1)
    repository_name = os.path.basename(remote_repo)

    directory = temp_path.joinpath("cache")
    repo_url_path = os.path.join(directory, repository_name)
    assert not os.path.exists(repo_url_path)

    if not os.path.exists(directory):
        os.mkdir(directory)

    if vcs_name == "svn":
        assert repository_name == "INITools"
        _create_svn_initools_repo(repo_url_path)
        repo_url_path = os.path.join(repo_url_path, "trunk")
    elif vcs_name == "git":
        # Don't use vcs_backend.obtain() here because we don't want a partial clone:
        # https://github.com/pypa/pip/issues/12719
        subprocess.check_call(
            ["git", "clone", vcs_url, repo_url_path],
        )
    else:
        vcs_backend = vcs.get_backend(vcs_name)
        assert vcs_backend is not None
        vcs_backend.obtain(repo_url_path, url=hide_url(remote_repo), verbosity=0)

    return f"{vcs_name}+{Path(repo_url_path).as_uri()}"


def local_repo(remote_repo: str, temp_path: Path) -> str:
    return local_checkout(remote_repo, temp_path).split("+", 1)[1]
