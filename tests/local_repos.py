import os
import subprocess
from pip.vcs import subversion, git, bazaar, mercurial
from pip.backwardcompat import urlretrieve
from tests.test_pip import path_to_url
from tests.pypi_server import PyPIProxy


if hasattr(subprocess, "check_call"):
    subprocess_call = subprocess.check_call
else:
    subprocess_call = subprocess.call


def _create_initools_repository():
    subprocess_call('svnadmin create INITools'.split(), cwd=_get_vcs_folder())


def _dump_initools_repository():
    filename, _ = urlretrieve('http://bitbucket.org/hltbra/pip-initools-dump/raw/8b55c908a320/INITools_modified.dump')
    initools_folder = os.path.join(_get_vcs_folder(), 'INITools')
    devnull = open(os.devnull, 'w')
    dump = open(filename)
    subprocess_call(['svnadmin', 'load', initools_folder], stdin=dump, stdout=devnull)
    dump.close()
    devnull.close()
    os.remove(filename)


def _create_svn_repository_for_initools():
    tests_cache = _get_vcs_folder()
    if not os.path.exists(os.path.join(tests_cache, 'INITools')):
        _create_initools_repository()
        _dump_initools_repository()


def _get_vcs_folder():
    folder_name = PyPIProxy.CACHE_PATH
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    return folder_name


def _get_vcs_and_checkout_url(remote_repository):
    tests_cache = _get_vcs_folder()
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
        repository_name = os.path.basename(remote_repository[:-len(branch)-1]) # remove the slash
    else:
        repository_name = os.path.basename(remote_repository)

    destination_path = os.path.join(tests_cache, repository_name)
    if not os.path.exists(destination_path):
        vcs_class(remote_repository).obtain(destination_path)
    return '%s+%s' % (vcs, path_to_url('/'.join([tests_cache, repository_name, branch])))


def local_checkout(remote_repo):
    if remote_repo.startswith('svn'):
        _create_svn_repository_for_initools()
    return _get_vcs_and_checkout_url(remote_repo)


def local_repo(remote_repo):
    return local_checkout(remote_repo).split('+', 1)[1]
