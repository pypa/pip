import zipfile
import textwrap
from os.path import join
from pip.download import path_to_url2
from tests.test_pip import here, reset_env, run_pip, write_file
from tests.path import Path
from tests.local_repos import local_checkout


def test_create_bundle():
    """
    Test making a bundle.  We'll grab one package from the filesystem
    (the FSPkg dummy package), one from vcs (initools) and one from an
    index (pip itself).

    """
    env = reset_env()
    fspkg = path_to_url2(Path(here)/'packages'/'FSPkg')
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
