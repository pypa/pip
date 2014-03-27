import pytest

from mock import patch

from pip.vcs.git import Git
from tests.lib import _create_test_package
from tests.lib.git_submodule_helpers import (
    _change_test_package_submodule,
    _pull_in_submodule_changes_to_module,
    _create_test_package_with_submodule,
)


def test_get_refs_should_return_tag_name_and_commit_pair(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'tag', '0.1', cwd=version_pkg_path)
    script.run('git', 'tag', '0.2', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    result = git.get_refs(version_pkg_path)
    assert result['0.1'] == commit, result
    assert result['0.2'] == commit, result


def test_get_refs_should_return_branch_name_and_commit_pair(script):
    version_pkg_path = _create_test_package(script)
    script.run('git', 'branch', 'branch0.1', cwd=version_pkg_path)
    commit = script.run(
        'git', 'rev-parse', 'HEAD',
        cwd=version_pkg_path
    ).stdout.strip()
    git = Git()
    result = git.get_refs(version_pkg_path)
    assert result['master'] == commit, result
    assert result['branch0.1'] == commit, result


def test_get_refs_should_ignore_no_branch(script):
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
    result = git.get_refs(version_pkg_path)
    assert result['master'] == commit, result
    assert result['branch0.1'] == commit, result


@patch('pip.vcs.git.Git.get_refs')
def test_check_rev_options_should_handle_branch_name(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': '123456'}
    git = Git()

    result = git.check_rev_options('master', '.', [])
    assert result == ['123456']


@patch('pip.vcs.git.Git.get_refs')
def test_check_rev_options_should_handle_tag_name(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': '123456'}
    git = Git()

    result = git.check_rev_options('0.1', '.', [])
    assert result == ['123456']


@patch('pip.vcs.git.Git.get_refs')
def test_check_rev_options_should_handle_ambiguous_commit(get_refs_mock):
    get_refs_mock.return_value = {'master': '123456', '0.1': '123456'}
    git = Git()

    result = git.check_rev_options('0.1', '.', [])
    assert result == ['123456'], result


# TODO(pnasrat) fix all helpers to do right things with paths on windows.
@pytest.mark.skipif("sys.platform == 'win32'")
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
