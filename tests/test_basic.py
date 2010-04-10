from os.path import abspath, exists, join, dirname, curdir, pardir
from test_pip import here, reset_env, run_pip, pyversion, lib_py, mkdir

def test_correct_pip_version():
    """
    Check we are running proper version of pip in run_pip.
    
    """
    reset_env()

    # where this source distribution lives
    base = abspath(join(dirname(__file__), pardir))

    # output will contain the directory of the invoked pip
    result = run_pip('--version')

    # compare the directory tree of the invoked pip with that of this source distribution
    import re,filecmp
    dir = re.match(r'\s*pip\s\S+\sfrom\s+(.*)\s\([^(]+\)$', result.stdout.replace('\r\n','\n')).group(1)
    diffs = filecmp.dircmp(join(base,'pip'), join(dir,'pip'))

    # If any non-matching .py files exist, we have a problem: run_pip
    # is picking up some other version!  N.B. if this project acquires
    # primary resources other than .py files, this code will need
    # maintenance
    mismatch_py = [x for x in diffs.left_only + diffs.right_only + diffs.diff_files if x.endswith('.py')]
    assert not mismatch_py, 'mismatched source files in %r and %r'% (join(base,'pip'), join(dir,'pip'))

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
    reset_env()
    result = run_pip('install', '-vvv', 'INITools==0.2', expect_error=True)
    assert (lib_py + 'site-packages/INITools-0.2-py%s.egg-info' % pyversion) in result.files_created, str(result)
    assert (lib_py + 'site-packages/initools') in result.files_created, sorted(result.files_created.keys())

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
    result = run_pip('install', '-e', 'svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev', expect_error=True)
    egg_link = result.files_created[lib_py + 'site-packages/INITools.egg-link']
    # FIXME: I don't understand why there's a trailing . here:
    assert egg_link.bytes.endswith('/test-scratch/src/initools\n.'), egg_link.bytes
    assert (lib_py + 'site-packages/easy-install.pth') in result.files_updated
    assert 'src/initools' in result.files_created
    assert 'src/initools/.svn' in result.files_created

def test_download_editable_to_custom_path():
    """
    Test downloading an editable using a relative custom src folder.
    
    """
    reset_env()
    mkdir('customdl')
    result = run_pip('install', '-e', 'svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev',
        '--src', 'customsrc', '--download', 'customdl',
        expect_error=True)
    assert 'customsrc/initools' in result.files_created
    assert 'customsrc/initools/setup.py' in result.files_created
    assert [filename for filename in result.files_created.keys() if filename.startswith('customdl/initools')]

def test_editable_no_install_followed_by_no_download():
    """
    Test installing an editable in two steps (first with --no-install, then with --no-download).
    
    """
    reset_env()

    result = run_pip('install', '-e', 'svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev',
        '--no-install', expect_error=True)
    assert lib_py + 'site-packages/INITools.egg-link' not in result.files_created
    assert 'src/initools' in result.files_created
    assert 'src/initools/.svn' in result.files_created

    result = run_pip('install', '-e', 'svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev',
        '--no-download',  expect_error=True)
    egg_link = result.files_created[lib_py + 'site-packages/INITools.egg-link']
    # FIXME: I don't understand why there's a trailing . here:
    assert egg_link.bytes.endswith('/test-scratch/src/initools\n.'), egg_link.bytes
    assert (lib_py + 'site-packages/easy-install.pth') in result.files_updated
    assert 'src/initools' not in result.files_created
    assert 'src/initools/.svn' not in result.files_created

def test_no_install_followed_by_no_download():
    """
    Test installing in two steps (first with --no-install, then with --no-download).
    
    """
    reset_env()

    result = run_pip('install', 'INITools==0.2', '--no-install', expect_error=True)
    assert (lib_py + 'site-packages/INITools-0.2-py%s.egg-info' % pyversion) not in result.files_created, str(result)
    assert (lib_py + 'site-packages/initools') not in result.files_created, sorted(result.files_created.keys())
    assert 'build/INITools' in result.files_created
    assert 'build/INITools/INITools.egg-info' in result.files_created

    result = run_pip('install', 'INITools==0.2', '--no-download',  expect_error=True)
    assert (lib_py + 'site-packages/INITools-0.2-py%s.egg-info' % pyversion) in result.files_created, str(result)
    assert (lib_py + 'site-packages/initools') in result.files_created, sorted(result.files_created.keys())
    assert 'build/INITools' not in result.files_created
    assert 'build/INITools/INITools.egg-info' not in result.files_created

def test_bad_install_with_no_download():
    """
    Test that --no-download behaves sensibly if the package source can't be found.
    
    """
    reset_env()

    result = run_pip('install', 'INITools==0.2', '--no-download',  expect_error=True)
    assert result.stdout.find("perhaps --no-download was used without first running an equivalent install with --no-install?") > 0

def test_install_dev_version_from_pypi():
    """
    Test using package==dev.
    
    """
    reset_env()
    result = run_pip('install', 'INITools==dev', expect_error=True)
    assert (lib_py + 'site-packages/initools') in result.files_created, str(result.stdout)

def test_install_editable_from_git():
    """
    Test cloning from Git.
    
    """
    reset_env()
    result = run_pip('install', '-e', 'git://github.com/jezdez/django-feedutil.git#egg=django-feedutil', expect_error=True)
    egg_link = result.files_created[lib_py + 'site-packages/django-feedutil.egg-link']
    # FIXME: I don't understand why there's a trailing . here:
    assert egg_link.bytes.endswith('/test-scratch/src/django-feedutil\n.'), egg_link.bytes
    assert (lib_py + 'site-packages/easy-install.pth') in result.files_updated
    assert 'src/django-feedutil' in result.files_created
    assert 'src/django-feedutil/.git' in result.files_created

def test_install_editable_from_hg():
    """
    Test cloning from Mercurial.
    
    """
    reset_env()
    result = run_pip('install', '-e', 'hg+http://bitbucket.org/ubernostrum/django-registration/#egg=django-registration', expect_error=True)
    egg_link = result.files_created[lib_py + 'site-packages/django-registration.egg-link']
    # FIXME: I don't understand why there's a trailing . here:
    assert egg_link.bytes.endswith('/test-scratch/src/django-registration\n.'), egg_link.bytes
    assert (lib_py + 'site-packages/easy-install.pth') in result.files_updated
    assert 'src/django-registration' in result.files_created
    assert 'src/django-registration/.hg' in result.files_created

def test_vcs_url_final_slash_normalization():
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    
    """
    reset_env()
    result = run_pip('install', '-e', 'hg+http://bitbucket.org/ubernostrum/django-registration#egg=django-registration', expect_error=True)
    assert 'pip-log.txt' not in result.files_created, result.files_created['pip-log.txt'].bytes

def test_install_editable_from_bazaar():
    """
    Test checking out from Bazaar.
    
    """
    reset_env()
    result = run_pip('install', '-e', 'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1/@174#egg=django-wikiapp', expect_error=True)
    egg_link = result.files_created[lib_py + 'site-packages/django-wikiapp.egg-link']
    # FIXME: I don't understand why there's a trailing . here:
    assert egg_link.bytes.endswith('/test-scratch/src/django-wikiapp\n.'), egg_link.bytes
    assert (lib_py + 'site-packages/easy-install.pth') in result.files_updated
    assert 'src/django-wikiapp' in result.files_created
    assert 'src/django-wikiapp/.bzr' in result.files_created

def test_vcs_url_urlquote_normalization():
    """
    Test that urlquoted characters are normalized for repo URL comparison.
    
    """
    reset_env()
    result = run_pip('install', '-e', 'bzr+http://bazaar.launchpad.net/~django-wikiapp/django-wikiapp/release-0.1#egg=django-wikiapp', expect_error=True)
    assert 'pip-log.txt' not in result.files_created, result.files_created['pip-log.txt'].bytes

def test_install_from_local_directory():
    """
    Test installing from a local directory.

    """
    reset_env()
    to_install = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', to_install, expect_error=False)
    assert (lib_py + 'site-packages/fspkg') in result.files_created, str(result.stdout)
    assert (lib_py + 'site-packages/FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)

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
    reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', curdir, cwd=run_from, expect_error=False)
    assert (lib_py + 'site-packages/fspkg') in result.files_created, str(result.stdout)
    assert (lib_py + 'site-packages/FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)

def test_install_pardir():
    """
    Test installing parent directory ('..').

    """
    reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg', 'fspkg'))
    result = run_pip('install', pardir, cwd=run_from, expect_error=False)
    assert (lib_py + 'site-packages/fspkg') in result.files_created, str(result.stdout)
    assert (lib_py + 'site-packages/FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)
