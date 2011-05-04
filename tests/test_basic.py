import re
import os
import filecmp
import textwrap
import sys
from os.path import abspath, join, curdir, pardir

from nose import SkipTest
from nose.tools import assert_raises
from mock import Mock, patch

from pip.util import rmtree, find_command
from pip.exceptions import BadCommand

from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from tests.path import Path


def test_correct_pip_version():
    """
    Check we are running proper version of pip in run_pip.
    """
    reset_env()

    # output is like:
    # pip PIPVERSION from PIPDIRECTORY (python PYVERSION)
    result = run_pip('--version')

    # compare the directory tree of the invoked pip with that of this source distribution
    dir = re.match(r'pip \d(\.[\d])+(\.(pre|post)\d+)? from (.*) \(python \d(.[\d])+\)$',
                   result.stdout).group(4)
    pip_folder = join(src_folder, 'pip')
    pip_folder_outputed = join(dir, 'pip')

    diffs = filecmp.dircmp(pip_folder, pip_folder_outputed)

    # If any non-matching .py files exist, we have a problem: run_pip
    # is picking up some other version!  N.B. if this project acquires
    # primary resources other than .py files, this code will need
    # maintenance
    mismatch_py = [x for x in diffs.left_only + diffs.right_only + diffs.diff_files if x.endswith('.py')]
    assert not mismatch_py, 'mismatched source files in %r and %r'% (pip_folder, pip_folder_outputed)


def test_pip_second_command_line_interface_works():
    """
    Check if ``pip-<PYVERSION>`` commands behaves equally
    """
    e = reset_env()
    result = e.run('pip-%s' % pyversion, 'install', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


#def test_distutils_configuration_setting():
#    """
#    Test the distutils-configuration-setting command (which is distinct from other commands).
#    """
    #print run_pip('-vv', '--distutils-cfg=easy_install:index_url:http://download.zope.org/ppix/', expect_error=True)
    #Script result: python ../../poacheggs.py -E .../poacheggs-tests/test-scratch -vv --distutils-cfg=easy_install:index_url:http://download.zope.org/ppix/
    #-- stdout: --------------------
    #Distutils config .../poacheggs-tests/test-scratch/lib/python.../distutils/distutils.cfg is writable
    #Replaced setting index_url
    #Updated .../poacheggs-tests/test-scratch/lib/python.../distutils/distutils.cfg
    #<BLANKLINE>
    #-- updated: -------------------
    #  lib/python2.4/distutils/distutils.cfg  (346 bytes)


def test_install_from_pypi():
    """
    Test installing a package from PyPI.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_mirrors():
    """
    Test installing a package from the PyPI mirrors.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--use-mirrors', '--no-index', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_mirrors_with_specific_mirrors():
    """
    Test installing a package from a specific PyPI mirror.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--use-mirrors', '--mirrors', "http://d.pypi.python.org/", '--no-index', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_editable_install():
    """
    Test editable installation.
    """
    reset_env()
    result = run_pip('install', '-e', 'INITools==0.2', expect_error=True)
    assert "--editable=INITools==0.2 should be formatted with svn+URL" in result.stdout
    assert len(result.files_created) == 1, result.files_created
    assert not result.files_updated, result.files_updated


def test_install_editable_from_svn():
    """
    Test checking out from svn.
    """
    reset_env()
    result = run_pip('install',
                     '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
    result.assert_installed('INITools', with_files=['.svn'])


def test_download_editable_to_custom_path():
    """
    Test downloading an editable using a relative custom src folder.
    """
    reset_env()
    mkdir('customdl')
    result = run_pip('install',
                     '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                     '--src',
                     'customsrc',
                     '--download',
                     'customdl')
    customsrc = Path('scratch')/'customsrc'/'initools'
    assert customsrc in result.files_created, sorted(result.files_created.keys())
    assert customsrc/'setup.py' in result.files_created, sorted(result.files_created.keys())

    customdl = Path('scratch')/'customdl'/'initools'
    customdl_files_created = [filename for filename in result.files_created
                                           if filename.startswith(customdl)]
    assert customdl_files_created


def test_editable_no_install_followed_by_no_download():
    """
    Test installing an editable in two steps (first with --no-install, then with --no-download).
    """
    reset_env()

    result = run_pip('install',
                     '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                     '--no-install', expect_error=True)
    result.assert_installed('INITools', without_egg_link=True, with_files=['.svn'])

    result = run_pip('install',
                     '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                     '--no-download', expect_error=True)
    result.assert_installed('INITools', without_files=[curdir, '.svn'])


def test_no_install_followed_by_no_download():
    """
    Test installing in two steps (first with --no-install, then with --no-download).
    """
    env = reset_env()

    egg_info_folder = env.site_packages/'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = env.site_packages/'initools'
    build_dir = env.venv/'build'/'INITools'

    result1 = run_pip('install', 'INITools==0.2', '--no-install', expect_error=True)
    assert egg_info_folder not in result1.files_created, str(result1)
    assert initools_folder not in result1.files_created, sorted(result1.files_created)
    assert build_dir in result1.files_created, result1.files_created
    assert build_dir/'INITools.egg-info' in result1.files_created

    result2 = run_pip('install', 'INITools==0.2', '--no-download', expect_error=True)
    assert egg_info_folder in result2.files_created, str(result2)
    assert initools_folder in result2.files_created, sorted(result2.files_created)
    assert build_dir not in result2.files_created
    assert build_dir/'INITools.egg-info' not in result2.files_created


def test_bad_install_with_no_download():
    """
    Test that --no-download behaves sensibly if the package source can't be found.
    """
    reset_env()
    result = run_pip('install', 'INITools==0.2', '--no-download', expect_error=True)
    assert "perhaps --no-download was used without first running "\
            "an equivalent install with --no-install?" in result.stdout


def test_install_dev_version_from_pypi():
    """
    Test using package==dev.
    """
    e = reset_env()
    result = run_pip('install', 'INITools==dev', expect_error=True)
    assert (e.site_packages / 'initools') in result.files_created, str(result.stdout)


def test_install_editable_from_git():
    """
    Test cloning from Git.
    """
    reset_env()
    args = ['install']
    args.extend(['-e',
                 '%s#egg=django-feedutil' %
                 local_checkout('git+http://github.com/jezdez/django-feedutil.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('django-feedutil', with_files=['.git'])


def test_install_editable_from_hg():
    """
    Test cloning from Mercurial.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s#egg=django-registration' %
                     local_checkout('hg+http://bitbucket.org/ubernostrum/django-registration'),
                     expect_error=True)
    result.assert_installed('django-registration', with_files=['.hg'])


def test_vcs_url_final_slash_normalization():
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s/#egg=django-registration' %
                     local_checkout('hg+http://bitbucket.org/ubernostrum/django-registration'),
                     expect_error=True)
    assert 'pip-log.txt' not in result.files_created, result.files_created['pip-log.txt'].bytes


def test_install_editable_from_bazaar():
    """
    Test checking out from Bazaar.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s/@174#egg=django-wikiapp' %
                     local_checkout('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1'),
                     expect_error=True)
    result.assert_installed('django-wikiapp', with_files=['.bzr'])


def test_vcs_url_urlquote_normalization():
    """
    Test that urlquoted characters are normalized for repo URL comparison.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s/#egg=django-wikiapp' %
                     local_checkout('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1'),
                     expect_error=True)
    assert 'pip-log.txt' not in result.files_created, result.files_created['pip-log.txt'].bytes


def test_install_from_local_directory():
    """
    Test installing from a local directory.
    """
    env = reset_env()
    to_install = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', to_install, expect_error=False)
    fspkg_folder = env.site_packages/'fspkg'
    egg_info_folder = env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_from_local_directory_with_no_setup_py():
    """
    Test installing from a local directory with no 'setup.py'.
    """
    reset_env()
    result = run_pip('install', here, expect_error=True)
    assert len(result.files_created) == 1, result.files_created
    assert 'pip-log.txt' in result.files_created, result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stdout


def test_install_curdir():
    """
    Test installing current directory ('.').
    """
    env = reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg'))
    # Python 2.4 Windows balks if this exists already
    egg_info = join(run_from, "FSPkg.egg-info")
    if os.path.isdir(egg_info):
        rmtree(egg_info)
    result = run_pip('install', curdir, cwd=run_from, expect_error=False)
    fspkg_folder = env.site_packages/'fspkg'
    egg_info_folder = env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_curdir_usersite_fails_in_old_python():
    """
    Test --user option on older Python versions (pre 2.6) fails intelligibly
    """
    if sys.version_info >= (2, 6):
        raise SkipTest()
    reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=True)
    assert '--user is only supported in Python version 2.6 and newer' in result.stdout


def test_install_curdir_usersite():
    """
    Test installing current directory ('.') into usersite
    """
    if sys.version_info < (2, 6):
        raise SkipTest()
    # FIXME distutils --user option seems to be broken in pypy
    if hasattr(sys, "pypy_version_info"):
        raise SkipTest()
    env = reset_env(use_distribute=True)
    run_from = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=False)
    fspkg_folder = env.user_site/'fspkg'
    egg_info_folder = env.user_site/'FSPkg-0.1dev-py%s.egg-info' % pyversion
    assert fspkg_folder in result.files_created, str(result.stdout)

    assert egg_info_folder in result.files_created, str(result)


def test_install_subversion_usersite_editable_with_distribute():
    """
    Test installing current directory ('.') into usersite after installing distribute
    """
    if sys.version_info < (2, 6):
        raise SkipTest()
    # FIXME distutils --user option seems to be broken in pypy
    if hasattr(sys, "pypy_version_info"):
        raise SkipTest()
    env = reset_env(use_distribute=True)
    (env.lib_path/'no-global-site-packages.txt').rm() # this one reenables user_site

    result = run_pip('install', '--user', '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
    result.assert_installed('INITools', use_user_site=True)


def test_install_subversion_usersite_editable_with_setuptools_fails():
    """
    Test installing current directory ('.') into usersite using setuptools fails
    """
    # --user only works on 2.6 or higher
    if sys.version_info < (2, 6):
        raise SkipTest()
    # We don't try to use setuptools for 3.X.
    elif sys.version_info >= (3,):
        raise SkipTest()
    env = reset_env()
    no_site_packages = env.lib_path/'no-global-site-packages.txt'
    if os.path.isfile(no_site_packages):
        no_site_packages.rm() # this re-enables user_site

    result = run_pip('install', '--user', '-e',
                     '%s#egg=initools-dev' %
                     local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                     expect_error=True)
    assert '--user --editable not supported with setuptools, use distribute' in result.stdout


def test_install_pardir():
    """
    Test installing parent directory ('..').
    """
    env = reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg', 'fspkg'))
    result = run_pip('install', pardir, cwd=run_from, expect_error=False)
    fspkg_folder = env.site_packages/'fspkg'
    egg_info_folder = env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_global_option():
    """
    Test using global distutils options.
    (In particular those that disable the actual install action)
    """
    reset_env()
    result = run_pip('install', '--global-option=--version', "INITools==0.1")
    assert '0.1\n' in result.stdout


def test_install_with_pax_header():
    """
    test installing from a tarball with pax header for python<2.6
    """
    reset_env()
    run_from = abspath(join(here, 'packages'))
    run_pip('install', 'paxpkg.tar.bz2', cwd=run_from)


def test_install_using_install_option_and_editable():
    """
    Test installing a tool using -e and --install-option
    """
    env = reset_env()
    folder = 'script_folder'
    mkdir(folder)
    url = 'git+git://github.com/pypa/virtualenv'
    result = run_pip('install', '-e', '%s#egg=virtualenv' %
                      local_checkout(url),
                     '--install-option=--script-dir=%s' % folder)
    virtualenv_bin = env.venv/'src'/'virtualenv'/folder/'virtualenv'+env.exe
    assert virtualenv_bin in result.files_created


def test_install_global_option_using_editable():
    """
    Test using global distutils options, but in an editable installation
    """
    reset_env()
    url = 'hg+http://bitbucket.org/runeh/anyjson'
    result = run_pip('install', '--global-option=--version',
                     '-e', '%s@0.2.5#egg=anyjson' %
                      local_checkout(url))
    assert '0.2.5\n' in result.stdout


def test_install_package_with_same_name_in_curdir():
    """
    Test installing a package with the same name of a local folder
    """
    env = reset_env()
    mkdir('mock==0.6')
    result = run_pip('install', 'mock==0.6')
    egg_folder = env.site_packages / 'mock-0.6.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


mock100_setup_py = textwrap.dedent('''\
                        from setuptools import setup
                        setup(name='mock',
                              version='100.1')''')


def test_install_folder_using_dot_slash():
    """
    Test installing a folder using pip install ./foldername
    """
    env = reset_env()
    mkdir('mock')
    pkg_path = env.scratch_path/'mock'
    write_file('setup.py', mock100_setup_py, pkg_path)
    result = run_pip('install', './mock')
    egg_folder = env.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_slash_in_the_end():
    r"""
    Test installing a folder using pip install foldername/ or foldername\
    """
    env = reset_env()
    mkdir('mock')
    pkg_path = env.scratch_path/'mock'
    write_file('setup.py', mock100_setup_py, pkg_path)
    result = run_pip('install', 'mock' + os.path.sep)
    egg_folder = env.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_relative_path():
    """
    Test installing a folder using pip install folder1/folder2
    """
    env = reset_env()
    mkdir('initools')
    mkdir(Path('initools')/'mock')
    pkg_path = env.scratch_path/'initools'/'mock'
    write_file('setup.py', mock100_setup_py, pkg_path)
    result = run_pip('install', Path('initools')/'mock')
    egg_folder = env.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_package_which_contains_dev_in_name():
    """
    Test installing package from pypi which contains 'dev' in name
    """
    env = reset_env()
    result = run_pip('install', 'django-devserver==0.0.4')
    devserver_folder = env.site_packages/'devserver'
    egg_info_folder = env.site_packages/'django_devserver-0.0.4-py%s.egg-info' % pyversion
    assert devserver_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_find_command_folder_in_path():
    """
    If a folder named e.g. 'git' is in PATH, and find_command is looking for
    the 'git' executable, it should not match the folder, but rather keep
    looking.
    """
    env = reset_env()
    mkdir('path_one')
    path_one = env.scratch_path/'path_one'
    mkdir(path_one/'foo')
    mkdir('path_two')
    path_two = env.scratch_path/'path_two'
    write_file(path_two/'foo', '# nothing')
    found_path = find_command('foo', map(str, [path_one, path_two]))
    assert found_path == path_two/'foo'


def test_does_not_find_command_because_there_is_no_path():
    """
    Test calling `pip.utils.find_command` when there is no PATH env variable
    """
    environ_before = os.environ
    os.environ = {}
    try:
        try:
            find_command('anycommand')
        except BadCommand:
            e = sys.exc_info()[1]
            assert e.args == ("Cannot find command 'anycommand'",)
        else:
            raise AssertionError("`find_command` should raise `BadCommand`")
    finally:
        os.environ = environ_before


@patch('pip.util.get_pathext')
@patch('os.path.isfile')
def test_find_command_trys_all_pathext(mock_isfile, getpath_mock):
    """
    If no pathext should check default list of extensions, if file does not
    exist.
    """
    mock_isfile.return_value = False
    # Patching os.pathsep failed on type checking
    old_sep = os.pathsep
    os.pathsep = ':'

    getpath_mock.return_value = os.pathsep.join([".COM", ".EXE"])

    paths = [os.path.join('path_one', f)  for f in ['foo.com', 'foo.exe', 'foo']]
    expected = [((p,),) for p in paths]

    try:
        assert_raises(BadCommand, find_command, 'foo', 'path_one')
        assert mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" % (mock_isfile.call_args_list, expected)
        assert getpath_mock.called, "Should call get_pathext"
    finally:
        os.pathsep = old_sep


@patch('pip.util.get_pathext')
@patch('os.path.isfile')
def test_find_command_trys_supplied_pathext(mock_isfile, getpath_mock):
    """
    If pathext supplied find_command should use all of its list of extensions to find file.
    """
    mock_isfile.return_value = False
    # Patching os.pathsep failed on type checking
    old_sep = os.pathsep
    os.pathsep = ':'
    getpath_mock.return_value = ".FOO"

    pathext = os.pathsep.join([".RUN", ".CMD"])

    paths = [os.path.join('path_one', f)  for f in ['foo.run', 'foo.cmd', 'foo']]
    expected = [((p,),) for p in paths]

    try:
        assert_raises(BadCommand, find_command, 'foo', 'path_one', pathext)
        assert mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" % (mock_isfile.call_args_list, expected)
        assert not getpath_mock.called, "Should not call get_pathext"
    finally:
        os.pathsep = old_sep
