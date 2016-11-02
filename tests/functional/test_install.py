import os
import sys
import textwrap
import glob

from os.path import join, curdir, pardir

import pytest

from pip import pep425tags
from pip.utils import appdirs, rmtree
from tests.lib import (pyversion, pyversion_tuple,
                       _create_test_package, _create_svn_repo, path_to_url,
                       requirements_file)
from tests.lib.local_repos import local_checkout
from tests.lib.path import Path


def test_without_setuptools(script, data):
    script.pip("uninstall", "setuptools", "-y")
    result = script.run(
        "python", "-c",
        "import pip; pip.main(["
        "'install', "
        "'INITools==0.2', "
        "'-f', '%s', "
        "'--no-binary=:all:'])" % data.packages,
        expect_error=True,
    )
    assert (
        "Could not import setuptools which is required to install from a "
        "source distribution."
        in result.stderr
    )
    assert "Please install setuptools" in result.stderr


def test_with_setuptools_and_import_error(script, data):
    # Make sure we get an ImportError while importing setuptools
    setuptools_init_path = script.site_packages_path.join(
        "setuptools", "__init__.py")
    with open(setuptools_init_path, 'a') as f:
        f.write('\nraise ImportError("toto")')

    result = script.run(
        "python", "-c",
        "import pip; pip.main(["
        "'install', "
        "'INITools==0.2', "
        "'-f', '%s', "
        "'--no-binary=:all:'])" % data.packages,
        expect_error=True,
    )
    assert (
        "Could not import setuptools which is required to install from a "
        "source distribution."
        in result.stderr
    )
    assert "Traceback " in result.stderr
    assert "ImportError: toto" in result.stderr


def test_pip_second_command_line_interface_works(script, data):
    """
    Check if ``pip<PYVERSION>`` commands behaves equally
    """
    # On old versions of Python, urllib3/requests will raise a warning about
    # the lack of an SSLContext.
    kwargs = {}
    if pyversion_tuple < (2, 7, 9):
        kwargs['expect_stderr'] = True

    args = ['pip%s' % pyversion]
    args.extend(['install', 'INITools==0.2'])
    args.extend(['-f', data.packages])
    result = script.run(*args, **kwargs)
    egg_info_folder = (
        script.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_from_pypi(script):
    """
    Test installing a package from PyPI.
    """
    result = script.pip('install', '-vvv', 'INITools==0.2')
    egg_info_folder = (
        script.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_editable_install(script):
    """
    Test editable installation.
    """
    result = script.pip('install', '-e', 'INITools==0.2', expect_error=True)
    assert (
        "INITools==0.2 should either be a path to a local project or a VCS url"
        in result.stderr
    )
    assert not result.files_created
    assert not result.files_updated


def test_install_editable_from_svn(script):
    """
    Test checking out from svn.
    """
    checkout_path = _create_test_package(script)
    repo_url = _create_svn_repo(script, checkout_path)
    result = script.pip(
        'install',
        '-e', 'svn+' + repo_url + '#egg=version-pkg'
    )
    result.assert_installed('version-pkg', with_files=['.svn'])


@pytest.mark.network
def test_download_editable_to_custom_path(script, tmpdir):
    """
    Test downloading an editable using a relative custom src folder.
    """
    script.scratch_path.join("customdl").mkdir()
    result = script.pip(
        'install',
        '-e',
        '%s#egg=initools-dev' %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        ),
        '--src',
        'customsrc',
        '--download',
        'customdl',
        expect_stderr=True
    )
    customsrc = Path('scratch') / 'customsrc' / 'initools'
    assert customsrc in result.files_created, (
        sorted(result.files_created.keys())
    )
    assert customsrc / 'setup.py' in result.files_created, (
        sorted(result.files_created.keys())
    )

    customdl = Path('scratch') / 'customdl' / 'initools'
    customdl_files_created = [
        filename for filename in result.files_created
        if filename.startswith(customdl)
    ]
    assert customdl_files_created
    assert ('DEPRECATION: pip install --download has been deprecated and will '
            'be removed in the future. Pip now has a download command that '
            'should be used instead.') in result.stderr


def _test_install_editable_from_git(script, tmpdir, wheel):
    """Test cloning from Git."""
    if wheel:
        script.pip('install', 'wheel')
    pkg_path = _create_test_package(script, name='testpackage', vcs='git')
    args = ['install', '-e', 'git+%s#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.git'])


def test_install_editable_from_git(script, tmpdir):
    _test_install_editable_from_git(script, tmpdir, False)


def test_install_editable_from_git_autobuild_wheel(script, tmpdir):
    _test_install_editable_from_git(script, tmpdir, True)


def test_install_editable_uninstalls_existing(data, script, tmpdir):
    """
    Test that installing an editable uninstalls a previously installed
    non-editable version.
    https://github.com/pypa/pip/issues/1548
    https://github.com/pypa/pip/pull/1552
    """
    to_install = data.packages.join("pip-test-package-0.1.tar.gz")
    result = script.pip_install_local(to_install)
    assert 'Successfully installed pip-test-package' in result.stdout
    result.assert_installed('piptestpackage', editable=False)

    result = script.pip(
        'install', '-e',
        '%s#egg=pip-test-package' %
        local_checkout(
            'git+http://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
    )
    result.assert_installed('pip-test-package', with_files=['.git'])
    assert 'Found existing installation: pip-test-package 0.1' in result.stdout
    assert 'Uninstalling pip-test-package-' in result.stdout
    assert 'Successfully uninstalled pip-test-package' in result.stdout


def test_install_editable_uninstalls_existing_from_path(script, data):
    """
    Test that installing an editable uninstalls a previously installed
    non-editable version from path
    """
    to_install = data.src.join('simplewheel-1.0')
    result = script.pip_install_local(to_install)
    assert 'Successfully installed simplewheel' in result.stdout
    simple_folder = script.site_packages / 'simple'
    result.assert_installed('simple', editable=False)
    assert simple_folder in result.files_created, str(result.stdout)

    result = script.pip(
        'install', '-e',
        to_install,
    )
    install_path = script.site_packages / 'simplewheel.egg-link'
    assert install_path in result.files_created, str(result)
    assert 'Found existing installation: simplewheel 1.0' in result.stdout
    assert 'Uninstalling simplewheel-' in result.stdout
    assert 'Successfully uninstalled simplewheel' in result.stdout
    assert simple_folder in result.files_deleted, str(result.stdout)


def test_install_editable_from_hg(script, tmpdir):
    """Test cloning from Mercurial."""
    pkg_path = _create_test_package(script, name='testpackage', vcs='hg')
    args = ['install', '-e', 'hg+%s#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.hg'])


def test_vcs_url_final_slash_normalization(script, tmpdir):
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    """
    pkg_path = _create_test_package(script, name='testpackage', vcs='hg')
    args = ['install', '-e', 'hg+%s/#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.hg'])


def test_install_editable_from_bazaar(script, tmpdir):
    """Test checking out from Bazaar."""
    pkg_path = _create_test_package(script, name='testpackage', vcs='bazaar')
    args = ['install', '-e', 'bzr+%s/#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.bzr'])


@pytest.mark.network
def test_vcs_url_urlquote_normalization(script, tmpdir):
    """
    Test that urlquoted characters are normalized for repo URL comparison.
    """
    script.pip(
        'install', '-e',
        '%s/#egg=django-wikiapp' %
        local_checkout(
            'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp'
            '/release-0.1',
            tmpdir.join("cache"),
        ),
    )


def test_install_from_local_directory(script, data):
    """
    Test installing from a local directory.
    """
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', to_install, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_quiet(script, data):
    """
    Test that install -q is actually quiet.
    """
    # Apparently if pip install -q is not actually quiet, then it breaks
    # everything. See:
    #   https://github.com/pypa/pip/issues/3418
    #   https://github.com/docker-library/python/issues/83
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', '-q', to_install, expect_error=False)
    assert result.stdout == ""
    assert result.stderr == ""


def test_hashed_install_success(script, data, tmpdir):
    """
    Test that installing various sorts of requirements with correct hashes
    works.

    Test file URLs and index packages (which become HTTP URLs behind the
    scenes).

    """
    file_url = path_to_url(
        (data.packages / 'simple-1.0.tar.gz').abspath)
    with requirements_file(
            'simple2==1.0 --hash=sha256:9336af72ca661e6336eb87bc7de3e8844d853e'
            '3848c2b9bbd2e8bf01db88c2c7\n'
            '{simple} --hash=sha256:393043e672415891885c9a2a0929b1af95fb866d6c'
            'a016b42d2e6ce53619b653'.format(simple=file_url),
            tmpdir) as reqs_file:
        script.pip_install_local('-r', reqs_file.abspath, expect_error=False)


def test_hashed_install_failure(script, data, tmpdir):
    """Test that wrong hashes stop installation.

    This makes sure prepare_files() is called in the course of installation
    and so has the opportunity to halt if hashes are wrong. Checks on various
    kinds of hashes are in test_req.py.

    """
    with requirements_file('simple2==1.0 --hash=sha256:9336af72ca661e6336eb87b'
                           'c7de3e8844d853e3848c2b9bbd2e8bf01db88c2c\n',
                           tmpdir) as reqs_file:
        result = script.pip_install_local('-r',
                                          reqs_file.abspath,
                                          expect_error=True)
    assert len(result.files_created) == 0


def test_install_from_local_directory_with_symlinks_to_directories(
        script, data):
    """
    Test installing from a local directory containing symlinks to directories.
    """
    to_install = data.packages.join("symlinks")
    result = script.pip('install', to_install, expect_error=False)
    pkg_folder = script.site_packages / 'symlinks'
    egg_info_folder = (
        script.site_packages / 'symlinks-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert pkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_from_local_directory_with_no_setup_py(script, data):
    """
    Test installing from a local directory with no 'setup.py'.
    """
    result = script.pip('install', data.root, expect_error=True)
    assert not result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stderr


def test_editable_install_from_local_directory_with_no_setup_py(script, data):
    """
    Test installing from a local directory with no 'setup.py'.
    """
    result = script.pip('install', '-e', data.root, expect_error=True)
    assert not result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stderr


@pytest.mark.skipif("sys.version_info < (2,7) or sys.version_info >= (3,4)")
@pytest.mark.xfail
def test_install_argparse_shadowed(script, data):
    # When argparse is in the stdlib, we support installing it
    # even though that's pretty useless because older packages did need to
    # depend on it, and not having its metadata will cause pkg_resources
    # requirements checks to fail // trigger easy-install, both of which are
    # bad.
    # XXX: Note, this test hits the outside-environment check, not the
    # in-stdlib check, because our tests run in virtualenvs...
    result = script.pip('install', 'argparse>=1.4')
    assert "Not uninstalling argparse" in result.stdout


@pytest.mark.skipif("sys.version_info < (3,4)")
def test_upgrade_argparse_shadowed(script, data):
    # If argparse is installed - even if shadowed for imported - we support
    # upgrading it and properly remove the older versions files.
    script.pip('install', 'argparse==1.3')
    result = script.pip('install', 'argparse>=1.4')
    assert "Not uninstalling argparse" not in result.stdout


def test_install_as_egg(script, data):
    """
    Test installing as egg, instead of flat install.
    """
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', to_install, '--egg', expect_error=True)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_folder = script.site_packages / 'FSPkg-0.1.dev0-py%s.egg' % pyversion
    assert fspkg_folder not in result.files_created, str(result.stdout)
    assert egg_folder in result.files_created, str(result)
    assert join(egg_folder, 'fspkg') in result.files_created, str(result)


def test_install_curdir(script, data):
    """
    Test installing current directory ('.').
    """
    run_from = data.packages.join("FSPkg")
    # Python 2.4 Windows balks if this exists already
    egg_info = join(run_from, "FSPkg.egg-info")
    if os.path.isdir(egg_info):
        rmtree(egg_info)
    result = script.pip('install', curdir, cwd=run_from, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_pardir(script, data):
    """
    Test installing parent directory ('..').
    """
    run_from = data.packages.join("FSPkg", "fspkg")
    result = script.pip('install', pardir, cwd=run_from, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_global_option(script):
    """
    Test using global distutils options.
    (In particular those that disable the actual install action)
    """
    result = script.pip(
        'install', '--global-option=--version', "INITools==0.1",
        expect_stderr=True)
    assert '0.1\n' in result.stdout


def test_install_with_pax_header(script, data):
    """
    test installing from a tarball with pax header for python<2.6
    """
    script.pip('install', 'paxpkg.tar.bz2', cwd=data.packages)


def test_install_with_hacked_egg_info(script, data):
    """
    test installing a package which defines its own egg_info class
    """
    run_from = data.packages.join("HackedEggInfo")
    result = script.pip('install', '.', cwd=run_from)
    assert 'Successfully installed hackedegginfo-0.0.0\n' in result.stdout


@pytest.mark.network
def test_install_using_install_option_and_editable(script, tmpdir):
    """
    Test installing a tool using -e and --install-option
    """
    folder = 'script_folder'
    script.scratch_path.join(folder).mkdir()
    url = 'git+git://github.com/pypa/pip-test-package'
    result = script.pip(
        'install', '-e', '%s#egg=pip-test-package' %
        local_checkout(url, tmpdir.join("cache")),
        '--install-option=--script-dir=%s' % folder,
        expect_stderr=True)
    script_file = (
        script.venv / 'src' / 'pip-test-package' /
        folder / 'pip-test-package' + script.exe
    )
    assert script_file in result.files_created


@pytest.mark.network
def test_install_global_option_using_editable(script, tmpdir):
    """
    Test using global distutils options, but in an editable installation
    """
    url = 'hg+http://bitbucket.org/runeh/anyjson'
    result = script.pip(
        'install', '--global-option=--version', '-e',
        '%s@0.2.5#egg=anyjson' % local_checkout(url, tmpdir.join("cache")),
        expect_stderr=True)
    assert 'Successfully installed anyjson' in result.stdout


@pytest.mark.network
def test_install_package_with_same_name_in_curdir(script):
    """
    Test installing a package with the same name of a local folder
    """
    script.scratch_path.join("mock==0.6").mkdir()
    result = script.pip('install', 'mock==0.6')
    egg_folder = script.site_packages / 'mock-0.6.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


mock100_setup_py = textwrap.dedent('''\
                        from setuptools import setup
                        setup(name='mock',
                              version='100.1')''')


def test_install_folder_using_dot_slash(script):
    """
    Test installing a folder using pip install ./foldername
    """
    script.scratch_path.join("mock").mkdir()
    pkg_path = script.scratch_path / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', './mock')
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_slash_in_the_end(script):
    r"""
    Test installing a folder using pip install foldername/ or foldername\
    """
    script.scratch_path.join("mock").mkdir()
    pkg_path = script.scratch_path / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', 'mock' + os.path.sep)
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_relative_path(script):
    """
    Test installing a folder using pip install folder1/folder2
    """
    script.scratch_path.join("initools").mkdir()
    script.scratch_path.join("initools", "mock").mkdir()
    pkg_path = script.scratch_path / 'initools' / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', Path('initools') / 'mock')
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_package_which_contains_dev_in_name(script):
    """
    Test installing package from pypi which contains 'dev' in name
    """
    result = script.pip('install', 'django-devserver==0.0.4')
    devserver_folder = script.site_packages / 'devserver'
    egg_info_folder = (
        script.site_packages / 'django_devserver-0.0.4-py%s.egg-info' %
        pyversion
    )
    assert devserver_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_package_with_target(script):
    """
    Test installing a package using pip install --target
    """
    target_dir = script.scratch_path / 'target'
    result = script.pip_install_local('-t', target_dir, "simple==1.0")
    assert Path('scratch') / 'target' / 'simple' in result.files_created, (
        str(result)
    )

    # Test repeated call without --upgrade, no files should have changed
    result = script.pip_install_local(
        '-t', target_dir, "simple==1.0", expect_stderr=True,
    )
    assert not Path('scratch') / 'target' / 'simple' in result.files_updated

    # Test upgrade call, check that new version is installed
    result = script.pip_install_local('--upgrade', '-t',
                                      target_dir, "simple==2.0")
    assert Path('scratch') / 'target' / 'simple' in result.files_updated, (
        str(result)
    )
    egg_folder = (
        Path('scratch') / 'target' / 'simple-2.0-py%s.egg-info' % pyversion)
    assert egg_folder in result.files_created, (
        str(result)
    )

    # Test install and upgrade of single-module package
    result = script.pip_install_local('-t', target_dir, 'singlemodule==0.0.0')
    singlemodule_py = Path('scratch') / 'target' / 'singlemodule.py'
    assert singlemodule_py in result.files_created, str(result)

    result = script.pip_install_local('-t', target_dir, 'singlemodule==0.0.1',
                                      '--upgrade')
    assert singlemodule_py in result.files_updated, str(result)


def test_install_package_with_root(script, data):
    """
    Test installing a package using pip install --root
    """
    root_dir = script.scratch_path / 'root'
    result = script.pip(
        'install', '--root', root_dir, '-f', data.find_links, '--no-index',
        'simple==1.0',
    )
    normal_install_path = (
        script.base_path / script.site_packages / 'simple-1.0-py%s.egg-info' %
        pyversion
    )
    # use distutils to change the root exactly how the --root option does it
    from distutils.util import change_root
    root_path = change_root(
        os.path.join(script.scratch, 'root'),
        normal_install_path
    )
    assert root_path in result.files_created, str(result)


def test_install_package_with_prefix(script, data):
    """
    Test installing a package using pip install --prefix
    """
    prefix_path = script.scratch_path / 'prefix'
    result = script.pip(
        'install', '--prefix', prefix_path, '-f', data.find_links,
        '--no-binary', 'simple', '--no-index', 'simple==1.0',
    )

    if hasattr(sys, "pypy_version_info"):
        path = script.scratch / 'prefix'
    else:
        path = script.scratch / 'prefix' / 'lib' / 'python{0}'.format(pyversion)  # noqa
    install_path = (
        path / 'site-packages' / 'simple-1.0-py{0}.egg-info'.format(pyversion)
    )
    assert install_path in result.files_created, str(result)


def test_install_editable_with_prefix(script):
    # make a dummy project
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.mkdir()
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """))

    site_packages = os.path.join(
        'prefix', 'lib', 'python{0}'.format(pyversion), 'site-packages')

    # make sure target path is in PYTHONPATH
    pythonpath = script.scratch_path / site_packages
    pythonpath.makedirs()
    script.environ["PYTHONPATH"] = pythonpath

    # install pkga package into the absolute prefix directory
    prefix_path = script.scratch_path / 'prefix'
    result = script.pip(
        'install', '--editable', pkga_path, '--prefix', prefix_path)

    # assert pkga is installed at correct location
    install_path = script.scratch / site_packages / 'pkga.egg-link'
    assert install_path in result.files_created, str(result)


def test_install_package_conflict_prefix_and_user(script, data):
    """
    Test installing a package using pip install --prefix --user errors out
    """
    prefix_path = script.scratch_path / 'prefix'
    result = script.pip(
        'install', '-f', data.find_links, '--no-index', '--user',
        '--prefix', prefix_path, 'simple==1.0',
        expect_error=True, quiet=True,
    )
    assert (
        "Can not combine '--user' and '--prefix'" in result.stderr
    )


# skip on win/py3 for now, see issue #782
@pytest.mark.skipif("sys.platform == 'win32' and sys.version_info >= (3,)")
def test_install_package_that_emits_unicode(script, data):
    """
    Install a package with a setup.py that emits UTF-8 output and then fails.

    Refs https://github.com/pypa/pip/issues/326
    """
    to_install = data.packages.join("BrokenEmitsUTF8")
    result = script.pip(
        'install', to_install, expect_error=True, expect_temp=True, quiet=True,
    )
    assert (
        'FakeError: this package designed to fail on install' in result.stdout
    )
    assert 'UnicodeDecodeError' not in result.stdout


def test_install_package_with_utf8_setup(script, data):
    """Install a package with a setup.py that declares a utf-8 encoding."""
    to_install = data.packages.join("SetupPyUTF8")
    script.pip('install', to_install)


def test_install_package_with_latin1_setup(script, data):
    """Install a package with a setup.py that declares a latin-1 encoding."""
    to_install = data.packages.join("SetupPyLatin1")
    script.pip('install', to_install)


def test_url_req_case_mismatch_no_index(script, data):
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages contains Upper-1.0.tar.gz and Upper-2.0.tar.gz
    'requiresupper' has install_requires = ['upper']
    """
    Upper = os.path.join(data.find_links, 'Upper-1.0.tar.gz')
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, Upper, 'requiresupper'
    )

    # only Upper-1.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Upper-1.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)
    egg_folder = script.site_packages / 'Upper-2.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)


def test_url_req_case_mismatch_file_index(script, data):
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages3 contains Dinner-1.0.tar.gz and Dinner-2.0.tar.gz
    'requiredinner' has install_requires = ['dinner']

    This test is similar to test_url_req_case_mismatch_no_index; that test
    tests behaviour when using "--no-index -f", while this one does the same
    test when using "--index-url". Unfortunately this requires a different
    set of packages as it requires a prepared index.html file and
    subdirectory-per-package structure.
    """
    Dinner = os.path.join(data.find_links3, 'dinner', 'Dinner-1.0.tar.gz')
    result = script.pip(
        'install', '--index-url', data.find_links3, Dinner, 'requiredinner'
    )

    # only Upper-1.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Dinner-1.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)
    egg_folder = script.site_packages / 'Dinner-2.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)


def test_url_incorrect_case_no_index(script, data):
    """
    Same as test_url_req_case_mismatch_no_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, "upper",
    )

    # only Upper-2.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Upper-1.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)
    egg_folder = script.site_packages / 'Upper-2.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_url_incorrect_case_file_index(script, data):
    """
    Same as test_url_req_case_mismatch_file_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        'install', '--index-url', data.find_links3, "dinner",
        expect_stderr=True,
    )

    # only Upper-2.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Dinner-1.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)
    egg_folder = script.site_packages / 'Dinner-2.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


@pytest.mark.network
def test_compiles_pyc(script):
    """
    Test installing with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "initools/__pycache__/__init__*.pyc"
    )

    assert any(exists)


@pytest.mark.network
def test_no_compiles_pyc(script, data):
    """
    Test installing from wheel with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--no-compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "initools/__pycache__/__init__*.pyc"
    )

    assert not any(exists)


def test_install_upgrade_editable_depending_on_other_editable(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """))
    script.pip('install', '--editable', pkga_path)
    result = script.pip('list', '--format=freeze')
    assert "pkga==0.1" in result.stdout

    script.scratch_path.join("pkgb").mkdir()
    pkgb_path = script.scratch_path / 'pkgb'
    pkgb_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkgb',
              version='0.1',
              install_requires=['pkga'])
    """))
    script.pip('install', '--upgrade', '--editable', pkgb_path, '--no-index')
    result = script.pip('list', '--format=freeze')
    assert "pkgb==0.1" in result.stdout


def test_install_subprocess_output_handling(script, data):
    args = ['install', data.src.join('chattymodule')]

    # Regular install should not show output from the chatty setup.py
    result = script.pip(*args)
    assert 0 == result.stdout.count("HELLO FROM CHATTYMODULE")
    script.pip("uninstall", "-y", "chattymodule")

    # With --verbose we should show the output.
    # Only count examples with sys.argv[1] == egg_info, because we call
    # setup.py multiple times, which should not count as duplicate output.
    result = script.pip(*(args + ["--verbose"]))
    assert 1 == result.stdout.count("HELLO FROM CHATTYMODULE egg_info")
    script.pip("uninstall", "-y", "chattymodule")

    # If the install fails, then we *should* show the output... but only once,
    # even if --verbose is given.
    result = script.pip(*(args + ["--global-option=--fail"]),
                        expect_error=True)
    assert 1 == result.stdout.count("I DIE, I DIE")

    result = script.pip(*(args + ["--global-option=--fail", "--verbose"]),
                        expect_error=True)
    assert 1 == result.stdout.count("I DIE, I DIE")


def test_install_log(script, data, tmpdir):
    # test that verbose logs go to "--log" file
    f = tmpdir.join("log.txt")
    args = ['--log=%s' % f,
            'install', data.src.join('chattymodule')]
    result = script.pip(*args)
    assert 0 == result.stdout.count("HELLO FROM CHATTYMODULE")
    with open(f, 'r') as fp:
        # one from egg_info, one from install
        assert 2 == fp.read().count("HELLO FROM CHATTYMODULE")


def test_install_topological_sort(script, data):
    args = ['install', 'TopoRequires4', '-f', data.packages]
    res = str(script.pip(*args, expect_error=False))
    order1 = 'TopoRequires, TopoRequires2, TopoRequires3, TopoRequires4'
    order2 = 'TopoRequires, TopoRequires3, TopoRequires2, TopoRequires4'
    assert order1 in res or order2 in res, res


def test_install_wheel_broken(script, data):
    script.pip('install', 'wheel')
    res = script.pip(
        'install', '--no-index', '-f', data.find_links, 'wheelbroken',
        expect_stderr=True)
    assert "Successfully installed wheelbroken-0.1" in str(res), str(res)


def test_cleanup_after_failed_wheel(script, data):
    script.pip('install', 'wheel')
    res = script.pip(
        'install', '--no-index', '-f', data.find_links, 'wheelbrokenafter',
        expect_stderr=True)
    # One of the effects of not cleaning up is broken scripts:
    script_py = script.bin_path / "script.py"
    assert script_py.exists, script_py
    shebang = open(script_py, 'r').readline().strip()
    assert shebang != '#!python', shebang
    # OK, assert that we *said* we were cleaning up:
    assert "Running setup.py clean for wheelbrokenafter" in str(res), str(res)


def test_install_builds_wheels(script, data):
    # NB This incidentally tests a local tree + tarball inputs
    # see test_install_editable_from_git_autobuild_wheel for editable
    # vcs coverage.
    script.pip('install', 'wheel')
    to_install = data.packages.join('requires_wheelbroken_upper')
    res = script.pip(
        'install', '--no-index', '-f', data.find_links,
        to_install, expect_stderr=True)
    expected = ("Successfully installed requires-wheelbroken-upper-0"
                " upper-2.0 wheelbroken-0.1")
    # Must have installed it all
    assert expected in str(res), str(res)
    root = appdirs.user_cache_dir('pip')
    wheels = []
    for top, dirs, files in os.walk(os.path.join(root, "wheels")):
        wheels.extend(files)
    # and built wheels for upper and wheelbroken
    assert "Running setup.py bdist_wheel for upper" in str(res), str(res)
    assert "Running setup.py bdist_wheel for wheelb" in str(res), str(res)
    # But not requires_wheel... which is a local dir and thus uncachable.
    assert "Running setup.py bdist_wheel for requir" not in str(res), str(res)
    # wheelbroken has to run install
    # into the cache
    assert wheels != [], str(res)
    # and installed from the wheel
    assert "Running setup.py install for upper" not in str(res), str(res)
    # the local tree can't build a wheel (because we can't assume that every
    # build will have a suitable unique key to cache on).
    assert "Running setup.py install for requires-wheel" in str(res), str(res)
    # wheelbroken has to run install
    assert "Running setup.py install for wheelb" in str(res), str(res)
    # We want to make sure we used the correct implementation tag
    assert wheels == [
        "Upper-2.0-{0}-none-any.whl".format(pep425tags.implementation_tag),
    ]


def test_install_no_binary_disables_building_wheels(script, data):
    script.pip('install', 'wheel')
    to_install = data.packages.join('requires_wheelbroken_upper')
    res = script.pip(
        'install', '--no-index', '--no-binary=upper', '-f', data.find_links,
        to_install, expect_stderr=True)
    expected = ("Successfully installed requires-wheelbroken-upper-0"
                " upper-2.0 wheelbroken-0.1")
    # Must have installed it all
    assert expected in str(res), str(res)
    root = appdirs.user_cache_dir('pip')
    wheels = []
    for top, dirs, files in os.walk(root):
        wheels.extend(files)
    # and built wheels for wheelbroken only
    assert "Running setup.py bdist_wheel for wheelb" in str(res), str(res)
    # But not requires_wheel... which is a local dir and thus uncachable.
    assert "Running setup.py bdist_wheel for requir" not in str(res), str(res)
    # Nor upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # wheelbroken has to run install
    # into the cache
    assert wheels != [], str(res)
    # the local tree can't build a wheel (because we can't assume that every
    # build will have a suitable unique key to cache on).
    assert "Running setup.py install for requires-wheel" in str(res), str(res)
    # And these two fell back to sdist based installed.
    assert "Running setup.py install for wheelb" in str(res), str(res)
    assert "Running setup.py install for upper" in str(res), str(res)


def test_install_no_binary_disables_cached_wheels(script, data):
    script.pip('install', 'wheel')
    # Seed the cache
    script.pip(
        'install', '--no-index', '-f', data.find_links,
        'upper')
    script.pip('uninstall', 'upper', '-y')
    res = script.pip(
        'install', '--no-index', '--no-binary=:all:', '-f', data.find_links,
        'upper', expect_stderr=True)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)


def test_install_editable_with_wrong_egg_name(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """))
    result = script.pip(
        'install', '--editable', 'file://%s#egg=pkgb' % pkga_path,
        expect_error=True)
    assert ("egg_info for package pkgb produced metadata "
            "for project name pkga. Fix your #egg=pkgb "
            "fragments.") in result.stderr
    assert "Successfully installed pkga" in str(result), str(result)


def test_install_tar_xz(script, data):
    try:
        import lzma  # noqa
    except ImportError:
        pytest.skip("No lzma support")
    res = script.pip('install', data.packages / 'singlemodule-0.0.1.tar.xz')
    assert "Successfully installed singlemodule-0.0.1" in res.stdout, res


def test_install_tar_lzma(script, data):
    try:
        import lzma  # noqa
    except ImportError:
        pytest.skip("No lzma support")
    res = script.pip('install', data.packages / 'singlemodule-0.0.1.tar.lzma')
    assert "Successfully installed singlemodule-0.0.1" in res.stdout, res


def test_double_install(script, data):
    """
    Test double install passing with two same version requirements
    """
    result = script.pip('install', 'pip', 'pip', expect_error=False)
    msg = "Double requirement given: pip (already in pip, name='pip')"
    assert msg not in result.stderr


def test_double_install_fail(script, data):
    """
    Test double install failing with two different version requirements
    """
    result = script.pip('install', 'pip==*', 'pip==7.1.2', expect_error=True)
    msg = ("Double requirement given: pip==7.1.2 (already in pip==*, "
           "name='pip')")
    assert msg in result.stderr


def test_install_incompatible_python_requires(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """))
    script.pip('install', 'setuptools>24.2')  # This should not be needed
    result = script.pip('install', pkga_path, expect_error=True)
    assert ("pkga requires Python '<1.0' "
            "but the running Python is ") in result.stderr


def test_install_incompatible_python_requires_editable(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """))
    script.pip('install', 'setuptools>24.2')  # This should not be needed
    result = script.pip(
        'install', '--editable=%s' % pkga_path, expect_error=True)
    assert ("pkga requires Python '<1.0' "
            "but the running Python is ") in result.stderr


def test_install_incompatible_python_requires_wheel(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              python_requires='<1.0',
              version='0.1')
    """))
    script.pip('install', 'setuptools>24.2')  # This should not be needed
    script.pip('install', 'wheel')
    script.run(
        'python', 'setup.py', 'bdist_wheel', '--universal', cwd=pkga_path)
    result = script.pip('install', './pkga/dist/pkga-0.1-py2.py3-none-any.whl',
                        expect_error=True)
    assert ("pkga requires Python '<1.0' "
            "but the running Python is ") in result.stderr


def test_install_compatible_python_requires(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              python_requires='>1.0',
              version='0.1')
    """))
    script.pip('install', 'setuptools>24.2')  # This should not be needed
    res = script.pip('install', pkga_path, expect_error=True)
    assert "Successfully installed pkga-0.1" in res.stdout, res


def test_install_environment_markers(script, data):
    # make a dummy project
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.mkdir()
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              install_requires=[
                'missing_pkg; python_version=="1.0"',
              ],
        )
    """))

    res = script.pip('install', '--no-index', pkga_path, expect_stderr=True)
    # missing_pkg should be ignored
    assert ("Ignoring missing-pkg: markers 'python_version == \"1.0\"' don't "
            "match your environment") in res.stderr, str(res)
    assert "Successfully installed pkga-0.1" in res.stdout, str(res)
