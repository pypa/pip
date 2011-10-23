from tests.test_pip import (reset_env, run_pip,
                      _create_test_package, _change_test_package_version)
from tests.local_repos import local_checkout


def test_install_editable_from_git_with_https():
    """
    Test cloning from Git with https.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s#egg=pip-test-package' %
                     local_checkout('git+https://github.com/pypa/pip-test-package.git'),
                     expect_error=True)
    result.assert_installed('pip-test-package', with_files=['.git'])


def test_git_with_sha1_revisions():
    """
    Git backend should be able to install from SHA1 revisions
    """
    env = reset_env()
    version_pkg_path = _create_test_package(env)
    _change_test_package_version(env, version_pkg_path)
    sha1 = env.run('git', 'rev-parse', 'HEAD~1', cwd=version_pkg_path).stdout.strip()
    run_pip('install', '-e', '%s@%s#egg=version_pkg' % ('git+file://' + version_pkg_path.abspath.replace('\\', '/'), sha1))
    version = env.run('version_pkg')
    assert '0.1' in version.stdout, version.stdout


def test_git_with_branch_name_as_revision():
    """
    Git backend should be able to install from branch names
    """
    env = reset_env()
    version_pkg_path = _create_test_package(env)
    env.run('git', 'checkout', '-b', 'test_branch', expect_stderr=True, cwd=version_pkg_path)
    _change_test_package_version(env, version_pkg_path)
    run_pip('install', '-e', '%s@test_branch#egg=version_pkg' % ('git+file://' + version_pkg_path.abspath.replace('\\', '/')))
    version = env.run('version_pkg')
    assert 'some different version' in version.stdout


def test_git_with_tag_name_as_revision():
    """
    Git backend should be able to install from tag names
    """
    env = reset_env()
    version_pkg_path = _create_test_package(env)
    env.run('git', 'tag', 'test_tag', expect_stderr=True, cwd=version_pkg_path)
    _change_test_package_version(env, version_pkg_path)
    run_pip('install', '-e', '%s@test_tag#egg=version_pkg' % ('git+file://' + version_pkg_path.abspath.replace('\\', '/')))
    version = env.run('version_pkg')
    assert '0.1' in version.stdout


def test_git_with_tag_name_and_update():
    """
    Test cloning a git repository and updating to a different version.
    """
    reset_env()
    result = run_pip('install', '-e', '%s#egg=pip-test-package' %
                     local_checkout('git+http://github.com/pypa/pip-test-package.git'),
                     expect_error=True)
    result.assert_installed('pip-test-package', with_files=['.git'])
    result = run_pip('install', '--global-option=--version', '-e',
                     '%s@0.1.1#egg=pip-test-package' %
                     local_checkout('git+http://github.com/pypa/pip-test-package.git'),
                     expect_error=True)
    assert '0.1.1\n' in result.stdout


def test_git_branch_should_not_be_changed():
    """
    Editable installations should not change branch
    related to issue #32 and #161
    """
    env = reset_env()
    run_pip('install', '-e', '%s#egg=pip-test-package' %
                local_checkout('git+http://github.com/pypa/pip-test-package.git'),
                expect_error=True)
    source_dir = env.venv_path/'src'/'pip-test-package'
    result = env.run('git', 'branch', cwd=source_dir)
    assert '* master' in result.stdout, result.stdout


def test_git_with_non_editable_unpacking():
    """
    Test cloning a git repository from a non-editable URL with a given tag.
    """
    reset_env()
    result = run_pip('install', '--global-option=--version', local_checkout(
                     'git+http://github.com/pypa/pip-test-package.git@0.1.1#egg=pip-test-package'
                     ), expect_error=True)
    assert '0.1.1\n' in result.stdout


def test_git_with_editable_where_egg_contains_dev_string():
    """
    Test cloning a git repository from an editable url which contains "dev" string
    """
    reset_env()
    result = run_pip('install', '-e', '%s#egg=django-devserver' %
                     local_checkout('git+git://github.com/dcramer/django-devserver.git'))
    result.assert_installed('django-devserver', with_files=['.git'])


def test_git_with_non_editable_where_egg_contains_dev_string():
    """
    Test cloning a git repository from a non-editable url which contains "dev" string
    """
    env = reset_env()
    result = run_pip('install', '%s#egg=django-devserver' %
                     local_checkout('git+git://github.com/dcramer/django-devserver.git'))
    devserver_folder = env.site_packages/'devserver'
    assert devserver_folder in result.files_created, str(result)


def test_git_with_ambiguous_revs():
    """
    Test git with two "names" (tag/branch) pointing to the same commit
    """
    env = reset_env()
    version_pkg_path = _create_test_package(env)
    package_url = 'git+file://%s@0.1#egg=version_pkg' % (version_pkg_path.abspath.replace('\\', '/'))
    env.run('git', 'tag', '0.1', cwd=version_pkg_path)
    result = run_pip('install', '-e', package_url)
    assert 'Could not find a tag or branch' not in result.stdout
    # it is 'version-pkg' instead of 'version_pkg' because
    # egg-link name is version-pkg.egg-link because it is a single .py module
    result.assert_installed('version-pkg', with_files=['.git'])
