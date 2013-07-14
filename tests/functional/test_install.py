import os
import sys
import textwrap
from os.path import abspath, join, curdir, pardir

from nose import SkipTest
from pip.util import rmtree
from tests.lib import tests_data, reset_env, run_pip, pyversion, mkdir, pip_install_local, write_file, find_links
from tests.lib.local_repos import local_checkout
from tests.lib.path import Path


def test_pip_second_command_line_interface_works():
    """
    Check if ``pip<PYVERSION>`` commands behaves equally
    """
    e = reset_env()

    args = ['pip%s' % pyversion]
    args.extend(['install', 'INITools==0.2'])
    result = e.run(*args)
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


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


def test_editable_install():
    """
    Test editable installation.
    """
    reset_env()
    result = run_pip('install', '-e', 'INITools==0.2', expect_error=True)
    assert "INITools==0.2 should either by a path to a local project or a VCS url" in result.stdout
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
    result = run_pip('install', 'INITools==dev',
                     '--allow-external', 'INITools',
                     '--allow-insecure', 'INITools',
                     expect_error=True)
    assert (e.site_packages / 'initools') in result.files_created, str(result.stdout)


def test_install_editable_from_git():
    """
    Test cloning from Git.
    """
    reset_env()
    args = ['install']
    args.extend(['-e',
                 '%s#egg=pip-test-package' %
                 local_checkout('git+http://github.com/pypa/pip-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('pip-test-package', with_files=['.git'])


def test_install_editable_from_hg():
    """
    Test cloning from Mercurial.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s#egg=ScriptTest' %
                     local_checkout('hg+https://bitbucket.org/ianb/scripttest'),
                     expect_error=True)
    result.assert_installed('ScriptTest', with_files=['.hg'])


def test_vcs_url_final_slash_normalization():
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    """
    reset_env()
    result = run_pip('install', '-e',
                     '%s/#egg=ScriptTest' %
                     local_checkout('hg+https://bitbucket.org/ianb/scripttest'),
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
    to_install = abspath(join(tests_data, 'packages', 'FSPkg'))
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
    result = run_pip('install', tests_data, expect_error=True)
    assert len(result.files_created) == 1, result.files_created
    assert 'pip-log.txt' in result.files_created, result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stdout


def test_editable_install_from_local_directory_with_no_setup_py():
    """
    Test installing from a local directory with no 'setup.py'.
    """
    reset_env()
    result = run_pip('install', '-e', tests_data, expect_error=True)
    assert len(result.files_created) == 1, result.files_created
    assert 'pip-log.txt' in result.files_created, result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stdout


def test_install_as_egg():
    """
    Test installing as egg, instead of flat install.
    """
    env = reset_env()
    to_install = abspath(join(tests_data, 'packages', 'FSPkg'))
    result = run_pip('install', to_install, '--egg', expect_error=False)
    fspkg_folder = env.site_packages/'fspkg'
    egg_folder = env.site_packages/'FSPkg-0.1dev-py%s.egg' % pyversion
    assert fspkg_folder not in result.files_created, str(result.stdout)
    assert egg_folder in result.files_created, str(result)
    assert join(egg_folder, 'fspkg') in result.files_created, str(result)


def test_install_curdir():
    """
    Test installing current directory ('.').
    """
    env = reset_env()
    run_from = abspath(join(tests_data, 'packages', 'FSPkg'))
    # Python 2.4 Windows balks if this exists already
    egg_info = join(run_from, "FSPkg.egg-info")
    if os.path.isdir(egg_info):
        rmtree(egg_info)
    result = run_pip('install', curdir, cwd=run_from, expect_error=False)
    fspkg_folder = env.site_packages/'fspkg'
    egg_info_folder = env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_pardir():
    """
    Test installing parent directory ('..').
    """
    env = reset_env()
    run_from = abspath(join(tests_data, 'packages', 'FSPkg', 'fspkg'))
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
    run_from = abspath(join(tests_data, 'packages'))
    run_pip('install', 'paxpkg.tar.bz2', cwd=run_from)


def test_install_with_hacked_egg_info():
    """
    test installing a package which defines its own egg_info class
    """
    reset_env()
    run_from = abspath(join(tests_data, 'packages', 'HackedEggInfo'))
    result = run_pip('install', '.', cwd=run_from)
    assert 'Successfully installed hackedegginfo\n' in result.stdout


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


def test_install_package_with_target():
    """
    Test installing a package using pip install --target
    """
    env = reset_env()
    target_dir = env.scratch_path/'target'
    result = run_pip('install', '-t', target_dir, "initools==0.1")
    assert Path('scratch')/'target'/'initools' in result.files_created, str(result)


def test_install_package_with_root():
    """
    Test installing a package using pip install --root
    """
    env = reset_env()
    root_dir = env.scratch_path/'root'
    result = run_pip('install', '--root', root_dir, '-f', find_links, '--no-index', 'simple==1.0')
    normal_install_path = env.root_path / env.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    #use distutils to change the root exactly how the --root option does it
    from distutils.util import change_root
    root_path = change_root(os.path.join(env.scratch, 'root'), normal_install_path)
    assert root_path in result.files_created, str(result)


def test_install_package_that_emits_unicode():
    """
    Install a package with a setup.py that emits UTF-8 output and then fails.
    This works fine in Python 2, but fails in Python 3 with:

    Traceback (most recent call last):
      ...
      File "/Users/marc/python/virtualenvs/py3.1-phpserialize/lib/python3.2/site-packages/pip-1.0.2-py3.2.egg/pip/__init__.py", line 230, in call_subprocess
        line = console_to_str(stdout.readline())
      File "/Users/marc/python/virtualenvs/py3.1-phpserialize/lib/python3.2/site-packages/pip-1.0.2-py3.2.egg/pip/backwardcompat.py", line 60, in console_to_str
        return s.decode(console_encoding)
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 17: ordinal not in range(128)

    Refs https://github.com/pypa/pip/issues/326
    """

    #skip on win/py3 for now, see issue #782
    if sys.platform == 'win32' and sys.version_info >= (3,):
        raise SkipTest()

    env = reset_env()
    to_install = os.path.abspath(os.path.join(tests_data, 'packages', 'BrokenEmitsUTF8'))
    result = run_pip('install', to_install, expect_error=True, expect_temp=True, quiet=True)
    assert 'FakeError: this package designed to fail on install' in result.stdout
    assert 'UnicodeDecodeError' not in result.stdout


def test_url_req_case_mismatch():
    """
    tar ball url requirements (with no egg fragment), that happen to have upper case project names,
    should be considered equal to later requirements that reference the project name using lower case.

    tests/packages contains Upper-1.0.tar.gz and Upper-2.0.tar.gz
    'requiresupper' has install_requires = ['upper']
    """
    env = reset_env()
    Upper = os.path.join(find_links, 'Upper-1.0.tar.gz')
    result = run_pip('install', '--no-index', '-f', find_links, Upper, 'requiresupper')

    #only Upper-1.0.tar.gz should get installed.
    egg_folder = env.site_packages / 'Upper-1.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)
    egg_folder = env.site_packages / 'Upper-2.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)

