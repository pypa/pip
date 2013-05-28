import zipfile
import textwrap
from os.path import abspath, exists, join
from pip.download import path_to_url2
from tests.lib import tests_data, reset_env, run_pip, write_file
from tests.lib.path import Path
from tests.lib.local_repos import local_checkout


def test_create_bundle():
    """
    Test making a bundle.  We'll grab one package from the filesystem
    (the FSPkg dummy package), one from vcs (initools) and one from an
    index (pip itself).

    """
    env = reset_env()
    fspkg = path_to_url2(Path(tests_data)/'packages'/'FSPkg')
    run_pip('install', '-e', fspkg)
    pkg_lines = textwrap.dedent('''\
            -e %s
            -e %s#egg=initools-dev
            pip''' % (fspkg, local_checkout('svn+http://svn.colorstudy.com/INITools/trunk')))
    write_file('bundle-req.txt', pkg_lines)
    # Create a bundle in env.scratch_path/ test.pybundle
    result = run_pip('bundle', '-r', env.scratch_path/ 'bundle-req.txt', env.scratch_path/ 'test.pybundle')
    bundle = result.files_after.get(join('scratch', 'test.pybundle'), None)
    assert bundle is not None

    files = zipfile.ZipFile(bundle.full).namelist()
    assert 'src/FSPkg/' in files
    assert 'src/initools/' in files
    assert 'build/pip/' in files


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
    fspkg = 'file://%s/FSPkg' %join(tests_data, 'packages')
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
