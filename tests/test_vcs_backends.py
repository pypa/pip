from test_pip import (reset_env, run_pip,
                      _create_test_package, _change_test_package_version)


def test_git_with_sha1_revisions():
    """
    Git backend should be able to install from SHA1 revisions
    """
    env = reset_env()
    version_pkg_path = _create_test_package(env)
    _change_test_package_version(env, version_pkg_path)
    sha1 = env.run('git', 'rev-parse', 'HEAD~1', cwd=version_pkg_path).stdout.strip()
    run_pip('install', '-e', '%s@%s#egg=version_pkg' % ('git+file://' + version_pkg_path, sha1))
    version = env.run('version_pkg')
    assert '0.1' in version.stdout, version.stdout

