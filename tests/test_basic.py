import re
import filecmp
import textwrap
from os.path import abspath, join, curdir, pardir
from test_pip import here, reset_env, run_pip, pyversion, mkdir, src_folder, write_file
from local_repos import local_checkout
from path import Path


def test_correct_pip_version():
    """
    Check we are running proper version of pip in run_pip.
    """
    reset_env()

    # output is like:
    # pip PIPVERSION from PIPDIRECTORY (python PYVERSION)
    result = run_pip('--version')

    # compare the directory tree of the invoked pip with that of this source distribution
    dir = re.match(r'pip \d(.[\d])+ from (.*) \(python \d(.[\d])+\)$',
                   result.stdout).group(2)
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


def test_distutils_configuration_setting():
    """
    Test the distutils-configuration-setting command (which is distinct from other commands).
    """
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
    result = run_pip('install', '-e',
                     '%s#egg=django-feedutil' %
                     local_checkout('git+http://github.com/jezdez/django-feedutil.git'),
                     expect_error=True)
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
