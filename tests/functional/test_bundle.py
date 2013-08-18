import os.path
import textwrap
import zipfile

from pip.download import path_to_url2
from tests.lib import tests_data
from tests.lib.local_repos import local_checkout


def test_create_bundle(tmpdir, script):
    """
    Test making a bundle.  We'll grab one package from the filesystem
    (the FSPkg dummy package), one from vcs (initools) and one from an
    index (pip itself).
    """
    fspkg = path_to_url2(os.path.join(tests_data, "packages", "FSPkg"))
    ctx = (
        fspkg,
        local_checkout("svn+http://svn.colorstudy.com/INITools/trunk"),
    )
    bundle_req_path = str(tmpdir.join("bundle-req.txt"))
    bundle_path = str(tmpdir.join("test.pybundle"))

    script.pip("install", "-e", fspkg)

    with open(bundle_req_path, "w") as bundle_req:
        bundle_req.write(textwrap.dedent("""
            -e %s
            -e %s#egg=initools-dev
            pip
        """ % ctx))

    # Create a bundle
    script.pip("bundle", "-r", bundle_req_path, bundle_path)

    # Ensure the bundle exists
    assert os.path.exists(bundle_path)

    # Ensure the bundle has the files we expect
    bundle = zipfile.ZipFile(bundle_path)

    assert "src/FSPkg/" in bundle.namelist()
    assert "src/initools/" in bundle.namelist()
    assert "build/pip/" in bundle.namelist()


def test_cleanup_after_create_bundle(tmpdir, script):
    """
    Test clean up after making a bundle. Make sure (build|src)-bundle/ dirs are
    removed but not src/.
    """
    # Install an editable to create a src/ dir
    script.pip(
        "install", "-e",
        (local_checkout("git+http://github.com/pypa/pip-test-package.git") +
            "#egg=pip-test-package"),
    )

    build_dir = script.virtualenv.join("build")
    src_dir = script.virtualenv.join("src")

    assert not build_dir.check(), "build/ dir still exists: %s" % build_dir
    assert src_dir.check(), "expected src/ dir doesn't exist: %s" % src_dir

    # Make the bundle
    fspkg = path_to_url2(os.path.join(tests_data, "packages", "FSPkg"))
    req_path = str(tmpdir.join("bundle-req.txt"))
    bundle_path = str(tmpdir.join("test.pybundle"))
    ctx = (
        fspkg,
        local_checkout("svn+http://svn.colorstudy.com/INITools/trunk"),
    )

    with open(req_path, "w") as req:
        req.write(textwrap.dedent("""
            -e %s
            -e %s#egg=initools-dev
            pip
        """ % ctx))

    script.pip("bundle", "-r", req_path, bundle_path)

    assert not os.listdir(script.cwd)

    # Make sure previously created src/ from editable still exists
    assert src_dir.check(), "expected src/ dir doesn't exist: %s" % src_dir
