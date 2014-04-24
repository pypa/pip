import os
import sys
import textwrap

import pytest

from tests.lib import (
    assert_all_changes, pyversion, _create_test_package,
    _change_test_package_version,
)
from tests.lib.local_repos import local_checkout


def test_no_upgrade_unless_requested(script):
    """
    No upgrade if not specifically requested.

    """
    script.pip('install', 'INITools==0.1', expect_error=True)
    result = script.pip('install', 'INITools', expect_error=True)
    assert not result.files_created, (
        'pip install INITools upgraded when it should not have'
    )


def test_upgrade_to_specific_version(script):
    """
    It does upgrade to specific version requested.

    """
    script.pip('install', 'INITools==0.1', expect_error=True)
    result = script.pip('install', 'INITools==0.2', expect_error=True)
    assert result.files_created, (
        'pip install with specific version did not upgrade'
    )
    assert (
        script.site_packages / 'INITools-0.1-py%s.egg-info' %
        pyversion in result.files_deleted
    )
    assert (
        script.site_packages / 'INITools-0.2-py%s.egg-info' %
        pyversion in result.files_created
    )


def test_upgrade_if_requested(script):
    """
    And it does upgrade if requested.

    """
    script.pip('install', 'INITools==0.1', expect_error=True)
    result = script.pip('install', '--upgrade', 'INITools', expect_error=True)
    assert result.files_created, 'pip install --upgrade did not upgrade'
    assert (
        script.site_packages / 'INITools-0.1-py%s.egg-info' %
        pyversion not in result.files_created
    )


def test_upgrade_with_newest_already_installed(script, data):
    """
    If the newest version of a package is already installed, the package should
    not be reinstalled and the user should be informed.
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple')
    result = script.pip(
        'install', '--upgrade', '-f', data.find_links, '--no-index', 'simple'
    )
    assert not result.files_created, 'simple upgraded when it should not have'
    assert 'already up-to-date' in result.stdout, result.stdout


def test_upgrade_force_reinstall_newest(script):
    """
    Force reinstallation of a package even if it is already at its newest
    version if --force-reinstall is supplied.
    """
    result = script.pip('install', 'INITools')
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip(
        'install', '--upgrade', '--force-reinstall', 'INITools'
    )
    assert result2.files_updated, 'upgrade to INITools 0.3 failed'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


def test_uninstall_before_upgrade(script):
    """
    Automatic uninstall-before-upgrade.

    """
    result = script.pip('install', 'INITools==0.2', expect_error=True)
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('install', 'INITools==0.3', expect_error=True)
    assert result2.files_created, 'upgrade to INITools 0.3 failed'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


def test_uninstall_before_upgrade_from_url(script):
    """
    Automatic uninstall-before-upgrade from URL.

    """
    result = script.pip('install', 'INITools==0.2', expect_error=True)
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip(
        'install',
        'http://pypi.python.org/packages/source/I/INITools/INITools-'
        '0.3.tar.gz',
        expect_error=True,
    )
    assert result2.files_created, 'upgrade to INITools 0.3 failed'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


def test_upgrade_to_same_version_from_url(script):
    """
    When installing from a URL the same version that is already installed, no
    need to uninstall and reinstall if --upgrade is not specified.

    """
    result = script.pip('install', 'INITools==0.3', expect_error=True)
    assert script.site_packages / 'initools' in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip(
        'install',
        'http://pypi.python.org/packages/source/I/INITools/INITools-'
        '0.3.tar.gz',
        expect_error=True,
    )
    assert not result2.files_updated, 'INITools 0.3 reinstalled same version'
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


def test_upgrade_from_reqs_file(script):
    """
    Upgrade from a requirements file.

    """
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""\
        PyLogo<0.4
        # and something else to test out:
        INITools==0.3
        """))
    install_result = script.pip(
        'install', '-r', script.scratch_path / 'test-req.txt'
    )
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""\
        PyLogo
        # and something else to test out:
        INITools
        """))
    script.pip(
        'install', '--upgrade', '-r', script.scratch_path / 'test-req.txt'
    )
    uninstall_result = script.pip(
        'uninstall', '-r', script.scratch_path / 'test-req.txt', '-y'
    )
    assert_all_changes(
        install_result,
        uninstall_result,
        [script.venv / 'build', 'cache', script.scratch / 'test-req.txt'],
    )


def test_uninstall_rollback(script, data):
    """
    Test uninstall-rollback (using test package with a setup.py
    crafted to fail on install).

    """
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', 'broken==0.1'
    )
    assert script.site_packages / 'broken.py' in result.files_created, list(
        result.files_created.keys()
    )
    result2 = script.pip(
        'install', '-f', data.find_links, '--no-index', 'broken==0.2broken',
        expect_error=True,
    )
    assert result2.returncode == 1, str(result2)
    assert script.run(
        'python', '-c', "import broken; print(broken.VERSION)"
    ).stdout == '0.1\n'
    assert_all_changes(
        result.files_after,
        result2,
        [script.venv / 'build', 'pip-log.txt'],
    )


# Issue #530 - temporarily disable flaky test
@pytest.mark.skipif
def test_editable_git_upgrade(script):
    """
    Test installing an editable git package from a repository, upgrading the
    repository, installing again, and check it gets the newer version
    """
    version_pkg_path = _create_test_package(script)
    script.pip(
        'install', '-e',
        '%s#egg=version_pkg' % ('git+file://' + version_pkg_path),
    )
    version = script.run('version_pkg')
    assert '0.1' in version.stdout
    _change_test_package_version(script, version_pkg_path)
    script.pip(
        'install', '-e',
        '%s#egg=version_pkg' % ('git+file://' + version_pkg_path),
    )
    version2 = script.run('version_pkg')
    assert 'some different version' in version2.stdout, (
        "Output: %s" % (version2.stdout)
    )


def test_should_not_install_always_from_cache(script):
    """
    If there is an old cached package, pip should download the newer version
    Related to issue #175
    """
    script.pip('install', 'INITools==0.2', expect_error=True)
    script.pip('uninstall', '-y', 'INITools')
    result = script.pip('install', 'INITools==0.1', expect_error=True)
    assert (
        script.site_packages / 'INITools-0.2-py%s.egg-info' %
        pyversion not in result.files_created
    )
    assert (
        script.site_packages / 'INITools-0.1-py%s.egg-info' %
        pyversion in result.files_created
    )


def test_install_with_ignoreinstalled_requested(script):
    """
    Test old conflicting package is completely ignored
    """
    script.pip('install', 'INITools==0.1', expect_error=True)
    result = script.pip('install', '-I', 'INITools==0.3', expect_error=True)
    assert result.files_created, 'pip install -I did not install'
    # both the old and new metadata should be present.
    assert os.path.exists(
        script.site_packages_path / 'INITools-0.1-py%s.egg-info' % pyversion
    )
    assert os.path.exists(
        script.site_packages_path / 'INITools-0.3-py%s.egg-info' % pyversion
    )


def test_upgrade_vcs_req_with_no_dists_found(script, tmpdir):
    """It can upgrade a VCS requirement that has no distributions otherwise."""
    req = "%s#egg=pip-test-package" % local_checkout(
        "git+http://github.com/pypa/pip-test-package.git",
        tmpdir.join("cache"),
    )
    script.pip("install", req)
    result = script.pip("install", "-U", req)
    assert not result.returncode


def test_upgrade_vcs_req_with_dist_found(script):
    """It can upgrade a VCS requirement that has distributions on the index."""
    # TODO(pnasrat) Using local_checkout fails on windows - oddness with the
    # test path urls/git.
    req = (
        "%s#egg=pretend" %
        (
            "git+git://github.com/alex/pretend@e7f26ad7dbcb4a02a4995aade4"
            "743aad47656b27"
        )
    )
    script.pip("install", req)
    result = script.pip("install", "-U", req)
    assert "pypi.python.org" not in result.stdout, result.stdout


class TestUpgradeSetuptools(object):
    """
    Tests for upgrading to setuptools (using pip from src tree)
    The tests use a *fixed* set of packages from our test packages dir
    note: virtualenv-1.9.1 contains distribute-0.6.34
    note: virtualenv-1.10 contains setuptools-0.9.7
    """

    def prep_ve(self, script, version, pip_src, distribute=False):
        self.script = script
        self.script.pip_install_local('virtualenv==%s' % version)
        args = ['virtualenv', self.script.scratch_path / 'VE']
        if distribute:
            args.insert(1, '--distribute')
        if version == "1.9.1" and not distribute:
            # setuptools 0.6 didn't support PYTHONDONTWRITEBYTECODE
            del self.script.environ["PYTHONDONTWRITEBYTECODE"]
        self.script.run(*args)
        if sys.platform == 'win32':
            bindir = "Scripts"
        else:
            bindir = "bin"
        self.ve_bin = self.script.scratch_path / 'VE' / bindir
        self.script.run(self.ve_bin / 'pip', 'uninstall', '-y', 'pip')
        self.script.run(
            self.ve_bin / 'python', 'setup.py', 'install',
            cwd=pip_src,
            expect_stderr=True,
        )

    @pytest.mark.skipif("sys.version_info >= (3,0)")
    def test_py2_from_setuptools_6_to_setuptools_7(
            self, script, data, virtualenv):
        self.prep_ve(script, '1.9.1', virtualenv.pip_source_dir)
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-use-wheel', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        assert (
            "Found existing installation: setuptools 0.6c11" in result.stdout
        )
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.8)" in result.stdout

    def test_py2_py3_from_distribute_6_to_setuptools_7(
            self, script, data, virtualenv):
        self.prep_ve(
            script, '1.9.1', virtualenv.pip_source_dir, distribute=True
        )
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        assert (
            "Found existing installation: distribute 0.6.34" in result.stdout
        )
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.8)" in result.stdout
        "distribute (0.7.3)" in result.stdout

    def test_from_setuptools_7_to_setuptools_7(self, script, data, virtualenv):
        self.prep_ve(script, '1.10', virtualenv.pip_source_dir)
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        assert "Found existing installation: setuptools 0.9.7" in result.stdout
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.8)" in result.stdout

    def test_from_setuptools_7_to_setuptools_7_using_wheel(
            self, script, data, virtualenv):
        self.prep_ve(script, '1.10', virtualenv.pip_source_dir)
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--use-wheel', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        assert "Found existing installation: setuptools 0.9.7" in result.stdout
        # only wheels use dist-info
        assert 'setuptools-0.9.8.dist-info' in str(result.files_created)
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.8)" in result.stdout

    # disabling intermittent travis failure:
    #   https://github.com/pypa/pip/issues/1379
    @pytest.mark.skipif("hasattr(sys, 'pypy_version_info')")
    def test_from_setuptools_7_to_setuptools_7_with_distribute_7_installed(
            self, script, data, virtualenv):
        self.prep_ve(
            script, '1.9.1', virtualenv.pip_source_dir, distribute=True
        )
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-index',
            '--find-links=%s' % data.find_links, 'setuptools==0.9.6'
        )
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.6)" in result.stdout
        "distribute (0.7.3)" in result.stdout
        result = self.script.run(
            self.ve_bin / 'pip', 'install', '--no-index',
            '--find-links=%s' % data.find_links, '-U', 'setuptools'
        )
        assert "Found existing installation: setuptools 0.9.6" in result.stdout
        result = self.script.run(self.ve_bin / 'pip', 'list')
        "setuptools (0.9.8)" in result.stdout
        "distribute (0.7.3)" in result.stdout
