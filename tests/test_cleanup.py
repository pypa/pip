import os
import textwrap
from os.path import abspath, exists, join
from tests.test_pip import (here, reset_env, run_pip,
                            write_file, mkdir, path_to_url)
from tests.local_repos import local_checkout
from tests.path import Path

find_links = path_to_url(os.path.join(here, 'packages'))

def test_cleanup_after_install():
    """
    Test clean up after installing a package.
    """
    env = reset_env()
    run_pip('install', '--no-index', '--find-links=%s' % find_links, 'simple')
    build = env.venv_path/"build"
    src = env.venv_path/"src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert not exists(src), "unexpected src/ dir exists: %s" % src
    env.assert_no_temp()

def test_no_clean_option_blocks_cleaning_after_install():
    """
    Test --no-clean option blocks cleaning after install
    """
    env = reset_env()
    result = run_pip('install', '--no-clean', '--no-index', '--find-links=%s' % find_links, 'simple')
    build = env.venv_path/'build'/'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


def test_no_clean_option_blocks_cleaning_after_wheel():
    """
    Test --no-clean option blocks cleaning after wheel build
    """
    env = reset_env(use_distribute=True)
    run_pip('install', 'wheel')
    result = run_pip('wheel', '--no-clean', '--no-index', '--find-links=%s' % find_links, 'simple')
    build = env.venv_path/'build'/'simple'
    assert exists(build), "build/simple should still exist %s" % str(result)


def test_cleanup_after_install_editable_from_hg():
    """
    Test clean up after cloning from Mercurial.

    """
    env = reset_env()
    run_pip('install',
            '-e',
            '%s#egg=ScriptTest' %
            local_checkout('hg+https://bitbucket.org/ianb/scripttest'),
            expect_error=True)
    build = env.venv_path/'build'
    src = env.venv_path/'src'
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src
    env.assert_no_temp()


def test_cleanup_after_install_from_local_directory():
    """
    Test clean up after installing from a local directory.

    """
    env = reset_env()
    to_install = abspath(join(here, 'packages', 'FSPkg'))
    run_pip('install', to_install, expect_error=False)
    build = env.venv_path/'build'
    src = env.venv_path/'src'
    assert not exists(build), "unexpected build/ dir exists: %s" % build
    assert not exists(src), "unexpected src/ dir exist: %s" % src
    env.assert_no_temp()


def test_cleanup_after_create_bundle():
    """
    Test clean up after making a bundle. Make sure (build|src)-bundle/ dirs are removed but not src/.

    """
    env = reset_env()
    # Install an editable to create a src/ dir.
    args = ['install']
    args.extend(['-e',
                 '%s#egg=pip-test-package' %
                    local_checkout('git+http://github.com/pypa/pip-test-package.git')])
    run_pip(*args)
    build = env.venv_path/"build"
    src = env.venv_path/"src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src

    # Make the bundle.
    fspkg = 'file://%s/FSPkg' %join(here, 'packages')
    pkg_lines = textwrap.dedent('''\
            -e %s
            -e %s#egg=initools-dev
            pip''' % (fspkg, local_checkout('svn+http://svn.colorstudy.com/INITools/trunk')))
    write_file('bundle-req.txt', pkg_lines)
    run_pip('bundle', '-r', 'bundle-req.txt', 'test.pybundle')
    build_bundle = env.scratch_path/"build-bundle"
    src_bundle = env.scratch_path/"src-bundle"
    assert not exists(build_bundle), "build-bundle/ dir still exists: %s" % build_bundle
    assert not exists(src_bundle), "src-bundle/ dir still exists: %s" % src_bundle
    env.assert_no_temp()

    # Make sure previously created src/ from editable still exists
    assert exists(src), "expected src dir doesn't exist: %s" % src


def test_no_install_and_download_should_not_leave_build_dir():
    """
    It should remove build/ dir if it was pip that created
    """
    env = reset_env()
    mkdir('downloaded_packages')
    assert not os.path.exists(env.venv_path/'/build')
    result = run_pip('install', '--no-install', 'INITools==0.2', '-d', 'downloaded_packages')
    assert Path('scratch')/'downloaded_packages/build' not in result.files_created, 'pip should not leave build/ dir'
    assert not os.path.exists(env.venv_path/'/build'), "build/ dir should be deleted"


def test_cleanup_req_satisifed_no_name():
    """
    Test cleanup when req is already satisfied, and req has no 'name'
    """
    #this test confirms Issue #420 is fixed
    #reqs with no 'name' that were already satisfied were leaving behind tmp build dirs
    #2 examples of reqs that would do this
    # 1) https://bitbucket.org/ianb/initools/get/tip.zip
    # 2) parent-0.1.tar.gz

    dist = abspath(join(here, 'packages', 'parent-0.1.tar.gz'))
    env = reset_env()
    result = run_pip('install', dist)
    result = run_pip('install', dist)
    build = env.venv_path/'build'
    assert not exists(build), "unexpected build/ dir exists: %s" % build
    env.assert_no_temp()


def test_download_should_not_delete_existing_build_dir():
    """
    It should not delete build/ if existing before run the command
    """
    env = reset_env()
    mkdir(env.venv_path/'build')
    f = open(env.venv_path/'build'/'somefile.txt', 'w')
    f.write('I am not empty!')
    f.close()
    run_pip('install', '--no-install', 'INITools==0.2', '-d', '.')
    f = open(env.venv_path/'build'/'somefile.txt')
    content = f.read()
    f.close()
    assert os.path.exists(env.venv_path/'build'), "build/ should be left if it exists before pip run"
    assert content == 'I am not empty!', "it should not affect build/ and its content"
    assert ['somefile.txt'] == os.listdir(env.venv_path/'build')

def test_cleanup_after_install_exception():
    """
    Test clean up after a 'setup.py install' exception.
    """
    env = reset_env()
    #broken==0.2broken fails during install; see packages readme file
    result = run_pip('install', '-f', find_links, '--no-index', 'broken==0.2broken', expect_error=True)
    build = env.venv_path/'build'
    assert not exists(build), "build/ dir still exists: %s" % result.stdout
    env.assert_no_temp()

def test_cleanup_after_egg_info_exception():
    """
    Test clean up after a 'setup.py egg_info' exception.
    """
    env = reset_env()
    #brokenegginfo fails during egg_info; see packages readme file
    result = run_pip('install', '-f', find_links, '--no-index', 'brokenegginfo==0.1', expect_error=True)
    build = env.venv_path/'build'
    assert not exists(build), "build/ dir still exists: %s" % result.stdout
    env.assert_no_temp()
