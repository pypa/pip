from __future__ import absolute_import

import os
import subprocess

from pip._vendor.six.moves.urllib import request as urllib_request

from pip._internal.utils.misc import hide_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.vcs import bazaar, git, mercurial, subversion
from tests.lib import path_to_url

if MYPY_CHECK_RUNNING:
    from tests.lib.path import Path


def _create_initools_repository(directory):
    subprocess.check_call('svnadmin create INITools'.split(), cwd=directory)


def _dump_initools_repository(directory):
    filename, _ = urllib_request.urlretrieve(
        'http://bitbucket.org/hltbra/pip-initools-dump/raw/8b55c908a320/'
        'INITools_modified.dump'
    )
    initools_folder = os.path.join(directory, 'INITools')
    devnull = open(os.devnull, 'w')
    dump = open(filename)
    subprocess.check_call(
        ['svnadmin', 'load', initools_folder],
        stdin=dump,
        stdout=devnull,
    )
    dump.close()
    devnull.close()
    os.remove(filename)


def _create_svn_repository_for_initools(directory):
    if not os.path.exists(os.path.join(directory, 'INITools')):
        _create_initools_repository(directory)
        _dump_initools_repository(directory)


def _get_vcs_and_checkout_url(remote_repository, directory):
    vcs_classes = {'svn': subversion.Subversion,
                   'git': git.Git,
                   'bzr': bazaar.Bazaar,
                   'hg': mercurial.Mercurial}
    default_vcs = 'svn'
    if '+' not in remote_repository:
        remote_repository = '%s+%s' % (default_vcs, remote_repository)
    vcs, repository_path = remote_repository.split('+', 1)
    vcs_class = vcs_classes[vcs]
    branch = ''
    if vcs == 'svn':
        branch = os.path.basename(remote_repository)
        # remove the slash
        repository_name = os.path.basename(
            remote_repository[:-len(branch) - 1]
        )
    else:
        repository_name = os.path.basename(remote_repository)

    destination_path = os.path.join(directory, repository_name)
    if not os.path.exists(destination_path):
        url = hide_url(remote_repository)
        vcs_class().obtain(destination_path, url=url)
    return '%s+%s' % (
        vcs,
        path_to_url('/'.join([directory, repository_name, branch])),
    )


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
    directory = temp_path.joinpath('cache')
    if not os.path.exists(directory):
        os.mkdir(directory)
        # os.makedirs(directory)

    if remote_repo.startswith('svn'):
        _create_svn_repository_for_initools(directory)
    return _get_vcs_and_checkout_url(remote_repo, directory)


def local_repo(remote_repo, temp_path):
    return local_checkout(remote_repo, temp_path).split('+', 1)[1]
