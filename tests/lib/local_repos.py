from __future__ import absolute_import

import os
import subprocess

from pip._vendor.six.moves.urllib import request as urllib_request

from pip._internal.utils.misc import hide_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.vcs import vcs
from tests.lib import path_to_url

if MYPY_CHECK_RUNNING:
    from tests.lib.path import Path


def _create_svn_initools_repo(initools_dir):
    """
    Create the SVN INITools repo.
    """
    directory = os.path.dirname(initools_dir)
    subprocess.check_call('svnadmin create INITools'.split(), cwd=directory)

    filename, _ = urllib_request.urlretrieve(
        'http://bitbucket.org/hltbra/pip-initools-dump/raw/8b55c908a320/'
        'INITools_modified.dump'
    )
    devnull = open(os.devnull, 'w')
    dump = open(filename)
    subprocess.check_call(
        ['svnadmin', 'load', initools_dir],
        stdin=dump,
        stdout=devnull,
    )
    dump.close()
    devnull.close()
    os.remove(filename)


def local_checkout(
    remote_repo,  # type: str
    temp_path,    # type: Path
):
    # type: (...) -> str
    """
    :param temp_path: the return value of the tmpdir fixture, which is a
        temp directory Path object unique to each test function invocation,
        created as a sub directory of the base temp directory.
    """
    assert '+' in remote_repo
    vcs_name = remote_repo.split('+', 1)[0]
    repository_name = os.path.basename(remote_repo)

    directory = temp_path.joinpath('cache')
    repo_url_path = os.path.join(directory, repository_name)
    assert not os.path.exists(repo_url_path)

    if not os.path.exists(directory):
        os.mkdir(directory)

    if vcs_name == 'svn':
        assert repository_name == 'INITools'
        _create_svn_initools_repo(repo_url_path)
        repo_url_path = os.path.join(repo_url_path, 'trunk')
    else:
        vcs_backend = vcs.get_backend(vcs_name)
        vcs_backend.obtain(repo_url_path, url=hide_url(remote_repo))

    return '{}+{}'.format(vcs_name, path_to_url(repo_url_path))


def local_repo(remote_repo, temp_path):
    return local_checkout(remote_repo, temp_path).split('+', 1)[1]
