import pytest
from mock import patch

from pip._internal.vcs.git import Git
from tests.lib import _create_test_package
from tests.lib.git_submodule_helpers import (
    _change_test_package_submodule, _create_test_package_with_submodule,
    _pull_in_submodule_changes_to_module
)


@pytest.mark.network
def test_get_short_refs_should_return_tag_name_and_commit_pair(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'tag', '0.1', cwd=version_pkg_path)
    script.run('git', 'tag', '0.2', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    result = git.get_short_refs(version_pkg_path)
    assert result['0.1'] == commit, result
    assert result['0.2'] == commit, result


@pytest.mark.network
def test_get_short_refs_should_return_branch_name_and_commit_pair(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'branch', 'branch0.1', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    result = git.get_short_refs(version_pkg_path)
    assert result['master'] == commit, result
    assert result['branch0.1'] == commit, result


@pytest.mark.network
def test_get_short_refs_should_ignore_no_branch(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'branch', 'branch0.1', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    # current branch here is "* (nobranch)"
    script.run(
        'git', 'checkout', commit,
        cwd=version_pkg_path,
        expect_stderr=True,
    )
    git = Git()
    result = git.get_short_refs(version_pkg_path)
    assert result['master'] == commit, result
    assert result['branch0.1'] == commit, result


def call_check_version(vcs, path, rev):
    rev_options = vcs.make_rev_options(rev)
    return vcs.check_version(path, rev_options)


@pytest.mark.network
def test_check_version(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'branch', 'branch0.1', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    assert call_check_version(git, version_pkg_path, commit)
    assert call_check_version(git, version_pkg_path, commit[:7])
    assert not call_check_version(git, version_pkg_path, 'branch0.1')
    assert not call_check_version(git, version_pkg_path, 'abc123')


@patch('pip._internal.vcs.git.Git.get_short_refs')
def test_check_rev_options_should_handle_branch_name(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': 'abc123'}
    git = Git()
    rev_options = git.make_rev_options('master')

    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == '123456'


@patch('pip._internal.vcs.git.Git.get_short_refs')
def test_check_rev_options_should_handle_tag_name(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': 'abc123'}
    git = Git()
    rev_options = git.make_rev_options('0.1')

    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == 'abc123'


@patch('pip._internal.vcs.git.Git.get_short_refs')
def test_check_rev_options_should_handle_ambiguous_commit(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': '123456'}
    git = Git()
    rev_options = git.make_rev_options('0.1')

    new_options = git.check_rev_options('.', rev_options)
    assert new_options.rev == '123456'


# TODO(pnasrat) fix all helpers to do right things with paths on windows.
@pytest.mark.skipif("sys.platform == 'win32'")
@pytest.mark.network
def test_check_submodule_addition(script):
    """
    Submodules are pulled in on install and updated on upgrade.
    """
    module_path, submodule_path = _create_test_package_with_submodule(script)

    install_result = script.pip(
        'install', '-e', 'git+' + module_path + '#egg=version_pkg'
    )
    assert (
        script.venv / 'src/version-pkg/testpkg/static/testfile'
        in install_result.files_created
    )

    _change_test_package_submodule(script, submodule_path)
    _pull_in_submodule_changes_to_module(script, module_path)

    # expect error because git may write to stderr
    update_result = script.pip(
        'install', '-e', 'git+' + module_path + '#egg=version_pkg',
        '--upgrade',
        expect_error=True,
    )

    assert (
        script.venv / 'src/version-pkg/testpkg/static/testfile2'
        in update_result.files_created
    )
