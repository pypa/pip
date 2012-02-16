import os
import textwrap
from os.path import abspath, exists, join
from tests.test_pip import (here, reset_env, run_pip, write_file, mkdir)
from tests.local_repos import local_checkout
from tests.path import Path


def test_cleanup_after_install_from_pypi():
    """
    Test clean up after installing a package from PyPI.

    """
    env = reset_env()
    run_pip('install', 'INITools==0.2', expect_error=True)
    build = env.scratch_path/"build"
    src = env.scratch_path/"src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert not exists(src), "unexpected src/ dir exists: %s" % src


def test_cleanup_after_install_editable_from_hg():
    """
    Test clean up after cloning from Mercurial.

    """
    env = reset_env()
    run_pip('install',
            '-e',
            '%s#egg=django-registration' %
            local_checkout('hg+http://bitbucket.org/ubernostrum/django-registration'),
            expect_error=True)
    build = env.venv_path/'build'
    src = env.venv_path/'src'
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src


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
