import os
import subprocess
import urllib
from pip.vcs import subversion, git, bazaar, mercurial
from path import Path
from test_pip import path_to_url, here


def _create_initools_repository():
    subprocess.call('svnadmin create INITools'.split(), cwd=_get_vcs_folder())


def _dump_initools_repository():
    filename, _ = urllib.urlretrieve('http://bitbucket.org/hltbra/pip-initools-dump/raw/d7a9beef1bbe/initools_colorstudy.dump')
    initools_folder = os.path.join(_get_vcs_folder())#, 'INITools')
    subprocess.call('svnadmin load . < %s' % filename, cwd=initools_folder, shell=True)


def _create_svn_repository_for_initools():
    vcs_repos = _get_vcs_folder()
    if not os.path.exists(os.path.join(vcs_repos, 'INITools')):
        _create_initools_repository()
        _dump_initools_repository()


def _get_vcs_folder():
    folder_name = here/'vcs_repos'
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    return folder_name


def _get_vcs_checkout_url(remote_repository):
    vcs_repos = _get_vcs_folder()
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
        # the INITools svn repository has a tree including INITools folder
        branch = 'INITools/' + branch
    else:
        repository_name = os.path.basename(remote_repository)

    destination_path = os.path.join(vcs_repos, repository_name)
    # svn doesnt work with clones
    # by now the repository is kept in vcs_repos folder
    if not os.path.exists(destination_path):
        vcs_class(remote_repository).obtain(destination_path)
    return path_to_url('/'.join([vcs_repos, repository_name, branch]))


def local_repo(remote_repo):
    if remote_repo.startswith('svn'):
        _create_svn_repository_for_initools()
    return _get_vcs_checkout_url(remote_repo)
