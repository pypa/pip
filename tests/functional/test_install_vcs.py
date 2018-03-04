import pytest

from tests.lib import (
    _change_test_package_version, _create_test_package, pyversion,
)
from tests.lib.local_repos import local_checkout


def _install_version_pkg(script, path, rev=None):
    """
    Install the version_pkg package, and return the version installed.

    Args:
      path: a tests.lib.path.Path object pointing to a Git repository
        containing the package.
      rev: an optional revision to install like a branch name or tag.
    """
    path = path.abspath.replace('\\', '/')
    revision = '' if rev is None else '@{}'.format(rev)
    url = 'git+file://{}{}#egg=version_pkg'.format(path, revision)
    script.pip('install', '-e', url)
    result = script.run('version_pkg')
    version = result.stdout.strip()

    return version


def test_git_install_again_after_changes(script):
    """
    Test installing a repository a second time without specifying a revision,
    and after updates to the remote repository.

    This test also checks that no warning message like the following gets
    logged on the update: "Did not find branch or tag ..., assuming ref or
    revision."
    """
    version_pkg_path = _create_test_package(script)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == '0.1'

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path)
    assert version == 'some different version'


def test_git_install_branch_again_after_branch_changes(script):
    """
    Test installing a branch again after the branch is updated in the remote
    repository.
    """
    version_pkg_path = _create_test_package(script)
    version = _install_version_pkg(script, version_pkg_path, rev='master')
    assert version == '0.1'

    _change_test_package_version(script, version_pkg_path)
    version = _install_version_pkg(script, version_pkg_path, rev='master')
    assert version == 'some different version'


@pytest.mark.network
def test_install_editable_from_git_with_https(script, tmpdir):
    """
    Test cloning from Git with https.
    """
    result = script.pip(
        'install', '-e',
        '%s#egg=pip-test-package' %
        local_checkout(
            'git+https://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        expect_error=True,
    )
    result.assert_installed('pip-test-package', with_files=['.git'])


@pytest.mark.network
def test_install_noneditable_git(script, tmpdir):
    """
    Test installing from a non-editable git URL with a given tag.
    """
    result = script.pip(
        'install',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1.1#egg=pip-test-package'
    )
    egg_info_folder = (
        script.site_packages /
        'pip_test_package-0.1.1-py%s.egg-info' % pyversion
    )
    result.assert_installed('piptestpackage',
                            without_egg_link=True,
                            editable=False)
    assert egg_info_folder in result.files_created, str(result)


@pytest.mark.network
def test_git_with_sha1_revisions(script):
    """
    Git backend should be able to install from SHA1 revisions
    """
    version_pkg_path = _create_test_package(script)
    _change_test_package_version(script, version_pkg_path)
    sha1 = script.run(
        'git', 'rev-parse', 'HEAD~1',
        cwd=version_pkg_path,
    ).stdout.strip()
    script.pip(
        'install', '-e',
        '%s@%s#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/'), sha1),
        expect_stderr=True
    )
    version = script.run('version_pkg')
    assert '0.1' in version.stdout, version.stdout


@pytest.mark.network
def test_git_with_branch_name_as_revision(script):
    """
    Git backend should be able to install from branch names
    """
    version_pkg_path = _create_test_package(script)
    script.run(
        'git', 'checkout', '-b', 'test_branch',
        expect_stderr=True,
        cwd=version_pkg_path,
    )
    _change_test_package_version(script, version_pkg_path)
    script.pip(
        'install', '-e', '%s@test_branch#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/'))
    )
    version = script.run('version_pkg')
    assert 'some different version' in version.stdout


@pytest.mark.network
def test_git_with_tag_name_as_revision(script):
    """
    Git backend should be able to install from tag names
    """
    version_pkg_path = _create_test_package(script)
    script.run(
        'git', 'tag', 'test_tag',
        expect_stderr=True,
        cwd=version_pkg_path,
    )
    _change_test_package_version(script, version_pkg_path)
    script.pip(
        'install', '-e', '%s@test_tag#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/'))
    )
    version = script.run('version_pkg')
    assert '0.1' in version.stdout


@pytest.mark.network
def test_git_with_ref_as_revision(script):
    """
    Git backend should be able to install from a ref
    """
    version_pkg_path = _create_test_package(script)
    script.run(
        'git', 'update-ref', 'refs/foo/bar', 'HEAD',
        expect_stderr=True,
        cwd=version_pkg_path,
    )
    _change_test_package_version(script, version_pkg_path)
    script.pip(
        'install', '-e', '%s@refs/foo/bar#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/')),
        expect_stderr=True
    )
    version = script.run('version_pkg')
    assert '0.1' in version.stdout


@pytest.mark.network
def test_git_with_tag_name_and_update(script, tmpdir):
    """
    Test cloning a git repository and updating to a different version.
    """
    result = script.pip(
        'install', '-e', '%s#egg=pip-test-package' %
        local_checkout(
            'git+https://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        expect_error=True,
    )
    result.assert_installed('pip-test-package', with_files=['.git'])
    result = script.pip(
        'install', '--global-option=--version', '-e',
        '%s@0.1.2#egg=pip-test-package' %
        local_checkout(
            'git+https://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        expect_error=True,
    )
    assert '0.1.2' in result.stdout


@pytest.mark.network
def test_git_branch_should_not_be_changed(script, tmpdir):
    """
    Editable installations should not change branch
    related to issue #32 and #161
    """
    script.pip(
        'install', '-e', '%s#egg=pip-test-package' %
        local_checkout(
            'git+https://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        expect_error=True,
    )
    source_dir = script.venv_path / 'src' / 'pip-test-package'
    result = script.run('git', 'branch', cwd=source_dir)
    assert '* master' in result.stdout, result.stdout


@pytest.mark.network
def test_git_with_non_editable_unpacking(script, tmpdir):
    """
    Test cloning a git repository from a non-editable URL with a given tag.
    """
    result = script.pip(
        'install', '--global-option=--version',
        local_checkout(
            'git+https://github.com/pypa/pip-test-package.git@0.1.2'
            '#egg=pip-test-package',
            tmpdir.join("cache")
        ),
        expect_error=True,
    )
    assert '0.1.2' in result.stdout


@pytest.mark.network
def test_git_with_editable_where_egg_contains_dev_string(script, tmpdir):
    """
    Test cloning a git repository from an editable url which contains "dev"
    string
    """
    result = script.pip(
        'install', '-e',
        '%s#egg=django-devserver' %
        local_checkout(
            'git+git://github.com/dcramer/django-devserver.git',
            tmpdir.join("cache")
        )
    )
    result.assert_installed('django-devserver', with_files=['.git'])


@pytest.mark.network
def test_git_with_non_editable_where_egg_contains_dev_string(script, tmpdir):
    """
    Test cloning a git repository from a non-editable url which contains "dev"
    string
    """
    result = script.pip(
        'install',
        '%s#egg=django-devserver' %
        local_checkout(
            'git+git://github.com/dcramer/django-devserver.git',
            tmpdir.join("cache")
        ),
    )
    devserver_folder = script.site_packages / 'devserver'
    assert devserver_folder in result.files_created, str(result)


@pytest.mark.network
def test_git_with_ambiguous_revs(script):
    """
    Test git with two "names" (tag/branch) pointing to the same commit
    """
    version_pkg_path = _create_test_package(script)
    package_url = (
        'git+file://%s@0.1#egg=version_pkg' %
        (version_pkg_path.abspath.replace('\\', '/'))
    )
    script.run('git', 'tag', '0.1', cwd=version_pkg_path)
    result = script.pip('install', '-e', package_url)
    assert 'Could not find a tag or branch' not in result.stdout
    # it is 'version-pkg' instead of 'version_pkg' because
    # egg-link name is version-pkg.egg-link because it is a single .py module
    result.assert_installed('version-pkg', with_files=['.git'])


@pytest.mark.network
def test_git_works_with_editable_non_origin_repo(script):
    # set up, create a git repo and install it as editable from a local
    # directory path
    version_pkg_path = _create_test_package(script)
    script.pip('install', '-e', version_pkg_path.abspath)

    # 'freeze'ing this should not fall over, but should result in stderr output
    # warning
    result = script.pip('freeze', expect_stderr=True)
    assert "Error when trying to get requirement" in result.stderr
    assert "Could not determine repository location" in result.stdout
    assert "version-pkg==0.1" in result.stdout


@pytest.mark.network
def test_reinstalling_works_with_editible_non_master_branch(script):
    """
    Reinstalling an editable installation should not assume that the "master"
    branch exists. See https://github.com/pypa/pip/issues/4448.
    """
    version_pkg_path = _create_test_package(script)

    # Switch the default branch to something other than 'master'
    script.run('git', 'branch', '-m', 'foobar', cwd=version_pkg_path)

    script.pip(
        'install', '-e',
        '%s#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/')),
    )
    version = script.run('version_pkg')
    assert '0.1' in version.stdout

    _change_test_package_version(script, version_pkg_path)
    script.pip(
        'install', '-e',
        '%s#egg=version_pkg' %
        ('git+file://' + version_pkg_path.abspath.replace('\\', '/')),
    )
    version = script.run('version_pkg')
    assert 'some different version' in version.stdout
