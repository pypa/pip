import textwrap
from os.path import abspath, exists, join
from test_pip import (here, reset_env, run_pip, write_file,
                       mercurial_repos, subversion_repos)


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
            'hg+file://%s/django-registration/#egg=django-registration' % mercurial_repos,
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
    run_pip('install', '-e', 'git://github.com/jezdez/django-feedutil.git#egg=django-feedutil')
    build = env.venv_path/"build"
    src = env.venv_path/"src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src

    # Make the bundle.
    fspkg = 'file://%s/FSPkg' %join(here, 'packages')
    pkg_lines = textwrap.dedent('''\
            -e %s
            -e svn+file://%sINITools/trunk#egg=initools-dev
            pip''' % (fspkg, subversion_repos))
    write_file('bundle-req.txt', pkg_lines)
    run_pip('bundle', '-r', 'bundle-req.txt', 'test.pybundle')
    build_bundle = env.scratch_path/"build-bundle"
    src_bundle = env.scratch_path/"src-bundle"
    assert not exists(build_bundle), "build-bundle/ dir still exists: %s" % build_bundle
    assert not exists(src_bundle), "src-bundle/ dir still exists: %s" % src_bundle

    # Make sure previously created src/ from editable still exists
    assert exists(src), "expected src dir doesn't exist: %s" % src
