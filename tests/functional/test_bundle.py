import zipfile
import textwrap
from os.path import abspath, exists, join
from pip.download import path_to_url
from tests.lib.local_repos import local_checkout


def test_create_bundle(script, tmpdir, data):
    """
    Test making a bundle.  We'll grab one package from the filesystem
    (the FSPkg dummy package), one from vcs (initools) and one from an
    index (pip itself).

    """
    fspkg = path_to_url(data.packages/'FSPkg')
    script.pip('install', '-e', fspkg)
    pkg_lines = textwrap.dedent('''\
            -e %s
            -e %s#egg=initools-dev
            pip''' % (fspkg, local_checkout('svn+http://svn.colorstudy.com/INITools/trunk', tmpdir.join("cache"))))
    script.scratch_path.join("bundle-req.txt").write(pkg_lines)
    # Create a bundle in env.scratch_path/ test.pybundle
    result = script.pip('bundle', '--no-use-wheel', '-r', script.scratch_path/ 'bundle-req.txt', script.scratch_path/ 'test.pybundle')
    bundle = result.files_after.get(join('scratch', 'test.pybundle'), None)
    assert bundle is not None

    files = zipfile.ZipFile(bundle.full).namelist()
    assert 'src/FSPkg/' in files
    assert 'src/initools/' in files
    assert 'build/pip/' in files


def test_cleanup_after_create_bundle(script, tmpdir, data):
    """
    Test clean up after making a bundle. Make sure (build|src)-bundle/ dirs are removed but not src/.

    """
    # Install an editable to create a src/ dir.
    args = ['install']
    args.extend(['-e',
                 '%s#egg=pip-test-package' %
                    local_checkout('git+http://github.com/pypa/pip-test-package.git', tmpdir.join("cache"))])
    script.pip(*args)
    build = script.venv_path/"build"
    src = script.venv_path/"src"
    assert not exists(build), "build/ dir still exists: %s" % build
    assert exists(src), "expected src/ dir doesn't exist: %s" % src

    # Make the bundle.
    fspkg = path_to_url(data.packages/'FSPkg')
    pkg_lines = textwrap.dedent('''\
            -e %s
            -e %s#egg=initools-dev
            pip''' % (fspkg, local_checkout('svn+http://svn.colorstudy.com/INITools/trunk', tmpdir.join("cache"))))
    script.scratch_path.join("bundle-req.txt").write(pkg_lines)
    script.pip('bundle', '--no-use-wheel', '-r', 'bundle-req.txt', 'test.pybundle')
    build_bundle = script.scratch_path/"build-bundle"
    src_bundle = script.scratch_path/"src-bundle"
    assert not exists(build_bundle), "build-bundle/ dir still exists: %s" % build_bundle
    assert not exists(src_bundle), "src-bundle/ dir still exists: %s" % src_bundle
    script.assert_no_temp()

    # Make sure previously created src/ from editable still exists
    assert exists(src), "expected src dir doesn't exist: %s" % src
