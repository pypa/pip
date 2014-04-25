from __future__ import with_statement

import textwrap
import os
import sys
from os.path import join, normpath
from tempfile import mkdtemp
from mock import patch
from tests.lib import assert_all_changes, pyversion
from tests.lib.local_repos import local_repo, local_checkout

from pip.util import rmtree


def test_simple_uninstall(script):
    """
    Test simple install and uninstall.

    """
    result = script.pip('install', 'INITools==0.2')
    assert join(script.site_packages, 'initools') in result.files_created, (
        sorted(result.files_created.keys())
    )
    # the import forces the generation of __pycache__ if the version of python
    # supports it
    script.run('python', '-c', "import initools")
    result2 = script.pip('uninstall', 'INITools', '-y')
    assert_all_changes(result, result2, [script.venv / 'build', 'cache'])


def test_uninstall_with_scripts(script):
    """
    Uninstall an easy_installed package with scripts.

    """
    result = script.run('easy_install', 'PyLogo', expect_stderr=True)
    easy_install_pth = script.site_packages / 'easy-install.pth'
    pylogo = sys.platform == 'win32' and 'pylogo' or 'PyLogo'
    assert(pylogo in result.files_updated[easy_install_pth].bytes)
    result2 = script.pip('uninstall', 'pylogo', '-y')
    assert_all_changes(
        result,
        result2,
        [script.venv / 'build', 'cache', easy_install_pth],
    )


def test_uninstall_easy_install_after_import(script):
    """
    Uninstall an easy_installed package after it's been imported

    """
    result = script.run('easy_install', 'INITools==0.2', expect_stderr=True)
    # the import forces the generation of __pycache__ if the version of python
    # supports it
    script.run('python', '-c', "import initools")
    result2 = script.pip('uninstall', 'INITools', '-y')
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            'cache',
            script.site_packages / 'easy-install.pth',
        ]
    )


def test_uninstall_namespace_package(script):
    """
    Uninstall a distribution with a namespace package without clobbering
    the namespace and everything in it.

    """
    result = script.pip('install', 'pd.requires==0.0.3', expect_error=True)
    assert join(script.site_packages, 'pd') in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'pd.find', '-y', expect_error=True)
    assert join(script.site_packages, 'pd') not in result2.files_deleted, (
        sorted(result2.files_deleted.keys())
    )
    assert join(script.site_packages, 'pd', 'find') in result2.files_deleted, (
        sorted(result2.files_deleted.keys())
    )


def test_uninstall_overlapping_package(script, data):
    """
    Uninstalling a distribution that adds modules to a pre-existing package
    should only remove those added modules, not the rest of the existing
    package.

    See: GitHub issue #355 (pip uninstall removes things it didn't install)
    """
    parent_pkg = data.packages.join("parent-0.1.tar.gz")
    child_pkg = data.packages.join("child-0.1.tar.gz")

    result1 = script.pip('install', parent_pkg, expect_error=False)
    assert join(script.site_packages, 'parent') in result1.files_created, (
        sorted(result1.files_created.keys())
    )
    result2 = script.pip('install', child_pkg, expect_error=False)
    assert join(script.site_packages, 'child') in result2.files_created, (
        sorted(result2.files_created.keys())
    )
    assert normpath(
        join(script.site_packages, 'parent/plugins/child_plugin.py')
    ) in result2.files_created, sorted(result2.files_created.keys())
    # The import forces the generation of __pycache__ if the version of python
    #  supports it
    script.run('python', '-c', "import parent.plugins.child_plugin, child")
    result3 = script.pip('uninstall', '-y', 'child', expect_error=False)
    assert join(script.site_packages, 'child') in result3.files_deleted, (
        sorted(result3.files_created.keys())
    )
    assert normpath(
        join(script.site_packages, 'parent/plugins/child_plugin.py')
    ) in result3.files_deleted, sorted(result3.files_deleted.keys())
    assert join(script.site_packages, 'parent') not in result3.files_deleted, (
        sorted(result3.files_deleted.keys())
    )
    # Additional check: uninstalling 'child' should return things to the
    # previous state, without unintended side effects.
    assert_all_changes(result2, result3, [])


def test_uninstall_console_scripts(script):
    """
    Test uninstalling a package with more files (console_script entry points,
    extra directories).
    """
    args = ['install']
    args.append('discover')
    result = script.pip(*args, **{"expect_error": True})
    assert script.bin / 'discover' + script.exe in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'discover', '-y', expect_error=True)
    assert_all_changes(result, result2, [script.venv / 'build', 'cache'])


def test_uninstall_easy_installed_console_scripts(script):
    """
    Test uninstalling package with console_scripts that is easy_installed.
    """
    args = ['easy_install']
    args.append('discover')
    result = script.run(*args, **{"expect_stderr": True})
    assert script.bin / 'discover' + script.exe in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'discover', '-y')
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            'cache',
            script.site_packages / 'easy-install.pth',
        ]
    )


def test_uninstall_editable_from_svn(script, tmpdir):
    """
    Test uninstalling an editable installation from svn.
    """
    result = script.pip(
        'install', '-e',
        '%s#egg=initools-dev' % local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache"),
        ),
    )
    result.assert_installed('INITools')
    result2 = script.pip('uninstall', '-y', 'initools')
    assert (script.venv / 'src' / 'initools' in result2.files_after)
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'src',
            script.venv / 'build',
            script.site_packages / 'easy-install.pth'
        ],
    )


def test_uninstall_editable_with_source_outside_venv(script, tmpdir):
    """
    Test uninstalling editable install from existing source outside the venv.

    """
    cache_dir = tmpdir.join("cache")

    try:
        temp = mkdtemp()
        tmpdir = join(temp, 'pip-test-package')
        _test_uninstall_editable_with_source_outside_venv(
            script,
            tmpdir,
            cache_dir,
        )
    finally:
        rmtree(temp)


def _test_uninstall_editable_with_source_outside_venv(
        script, tmpdir, cache_dir):
    result = script.run(
        'git', 'clone',
        local_repo(
            'git+git://github.com/pypa/pip-test-package',
            cache_dir,
        ),
        tmpdir,
        expect_stderr=True,
    )
    result2 = script.pip('install', '-e', tmpdir)
    assert join(
        script.site_packages, 'pip-test-package.egg-link'
    ) in result2.files_created, list(result2.files_created.keys())
    result3 = script.pip('uninstall', '-y',
                         'pip-test-package', expect_error=True)
    assert_all_changes(
        result,
        result3,
        [script.venv / 'build', script.site_packages / 'easy-install.pth'],
    )


def test_uninstall_from_reqs_file(script, tmpdir):
    """
    Test uninstall from a requirements file.

    """
    script.scratch_path.join("test-req.txt").write(
        textwrap.dedent("""
            -e %s#egg=initools-dev
            # and something else to test out:
            PyLogo<0.4
        """) %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        )
    )
    result = script.pip('install', '-r', 'test-req.txt')
    script.scratch_path.join("test-req.txt").write(
        textwrap.dedent("""
            # -f, -i, and --extra-index-url should all be ignored by uninstall
            -f http://www.example.com
            -i http://www.example.com
            --extra-index-url http://www.example.com

            -e %s#egg=initools-dev
            # and something else to test out:
            PyLogo<0.4
        """) %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        )
    )
    result2 = script.pip('uninstall', '-r', 'test-req.txt', '-y')
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            script.venv / 'src',
            script.scratch / 'test-req.txt',
            script.site_packages / 'easy-install.pth',
        ],
    )


def test_uninstall_as_egg(script, data):
    """
    Test uninstall package installed as egg.
    """
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', to_install, '--egg', expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_folder = script.site_packages / 'FSPkg-0.1dev-py%s.egg' % pyversion
    assert fspkg_folder not in result.files_created, str(result.stdout)
    assert egg_folder in result.files_created, str(result)

    result2 = script.pip('uninstall', 'FSPkg', '-y', expect_error=True)
    assert_all_changes(
        result,
        result2,
        [
            script.venv / 'build',
            'cache',
            script.site_packages / 'easy-install.pth',
        ],
    )


@patch('pip.req.req_uninstall.logger')
def test_uninstallpathset_no_paths(mock_logger):
    """
    Test UninstallPathSet logs notification when there are no paths to
    uninstall
    """
    from pip.req.req_uninstall import UninstallPathSet
    from pkg_resources import get_distribution
    test_dist = get_distribution('pip')
    # ensure that the distribution is "local"
    with patch("pip.req.req_uninstall.dist_is_local") as mock_dist_is_local:
        mock_dist_is_local.return_value = True
        uninstall_set = UninstallPathSet(test_dist)
        uninstall_set.remove()  # with no files added to set
    mock_logger.notify.assert_any_call(
        "Can't uninstall 'pip'. No files were found to uninstall.",
    )


@patch('pip.req.req_uninstall.logger')
def test_uninstallpathset_non_local(mock_logger):
    """
    Test UninstallPathSet logs notification and returns (with no exception)
    when dist is non-local
    """
    nonlocal_path = os.path.abspath("/nonlocal")
    from pip.req.req_uninstall import UninstallPathSet
    from pkg_resources import get_distribution
    test_dist = get_distribution('pip')
    test_dist.location = nonlocal_path
    # ensure that the distribution is "non-local"
    # setting location isn't enough, due to egg-link file checking for
    # develop-installs
    with patch("pip.req.req_uninstall.dist_is_local") as mock_dist_is_local:
        mock_dist_is_local.return_value = False
        uninstall_set = UninstallPathSet(test_dist)
        # with no files added to set; which is the case when trying to remove
        # non-local dists
        uninstall_set.remove()
    mock_logger.notify.assert_any_call(
        "Not uninstalling pip at %s, outside environment %s" %
        (nonlocal_path, sys.prefix)
    )
    mock_logger.notify.mock_calls


def test_uninstall_wheel(script, data):
    """
    Test uninstalling a wheel
    """
    package = data.packages.join("simple.dist-0.1-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index')
    dist_info_folder = script.site_packages / 'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created
    result2 = script.pip('uninstall', 'simple.dist', '-y')
    assert_all_changes(result, result2, [])
