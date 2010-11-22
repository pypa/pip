from test_pip import (reset_env, run_pip, pyversion,
                      _create_test_package, _change_test_package_version)
from local_repos import local_checkout


def test_install_editable_from_git_with_https():
    """
    Test cloning from Git with https.
    """
    env = reset_env()
    result = run_pip('install', '-e',
                     '%s#egg=django-feedutil' %
                     local_checkout('git+https://github.com/jezdez/django-feedutil.git'),
                     expect_error=True)
    result.assert_installed('django-feedutil', with_files=['.git'])


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
    result = run_pip('install', '-e', '%s#egg=django-staticfiles' %
                     local_checkout('git+http://github.com/jezdez/django-staticfiles.git'),
                     expect_error=True)
    result.assert_installed('django-staticfiles', with_files=['.git'])
    result = run_pip('install', '--global-option=--version', '-e',
                     '%s@0.3.1#egg=django-staticfiles' %
                     local_checkout('git+http://github.com/jezdez/django-staticfiles.git'),
                     expect_error=True)
    assert '0.3.1\n' in result.stdout


def test_git_branch_should_not_be_changed():
    """
    Editable installations should not change branch
    related to issue #32 and #161
    """
    env = reset_env()
    run_pip('install', '-e', '%s#egg=django-staticfiles' %
                local_checkout('git+http://github.com/jezdez/django-staticfiles.git'),
                expect_error=True)
    source_dir = env.venv_path/'src'/'django-staticfiles'
    result = env.run('git', 'branch', cwd=source_dir)
    assert '* master' in result.stdout

def test_git_with_non_editable_unpacking():
    """
    Test cloning a git repository from a non-editable URL with a given tag.
    """
    reset_env()
    result = run_pip('install', '--global-option=--version', local_checkout(
                     'git+http://github.com/jezdez/django-staticfiles.git@0.3.1#egg=django-staticfiles'
                     ), expect_error=True)
    assert '0.3.1\n' in result.stdout
