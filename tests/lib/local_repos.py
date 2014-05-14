from __future__ import absolute_import

import os
import subprocess
from pip.vcs import subversion, git, bazaar, mercurial
from pip.compat import urlretrieve
from tests.lib import path_to_url


if hasattr(subprocess, "check_call"):
    subprocess_call = subprocess.check_call
else:
    subprocess_call = subprocess.call


def _create_initools_repository(directory):
    subprocess_call('svnadmin create INITools'.split(), cwd=directory)


def _dump_initools_repository(directory):
    filename, _ = urlretrieve(
        'http://bitbucket.org/hltbra/pip-initools-dump/raw/8b55c908a320/'
        'INITools_modified.dump'
    )
    initools_folder = os.path.join(directory, 'INITools')
    devnull = open(os.devnull, 'w')
    dump = open(filename)
    subprocess_call(
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
        vcs_class(remote_repository).obtain(destination_path)
    return '%s+%s' % (
        vcs,
        path_to_url('/'.join([directory, repository_name, branch])),
    )


def local_checkout(remote_repo, directory):
    if not os.path.exists(directory):
        os.mkdir(directory)
        # os.makedirs(directory)

    if remote_repo.startswith('svn'):
        _create_svn_repository_for_initools(directory)
    return _get_vcs_and_checkout_url(remote_repo, directory)


def local_repo(remote_repo, directory):
    return local_checkout(remote_repo, directory).split('+', 1)[1]
