
import zipfile
from os.path import abspath, join, dirname, pardir
from test_pip import here, reset_env, run_pip, pyversion, lib_py
from test_pip import write_file

def test_1():
    '''
    Test making a bundle.  We'll grab one package from the filesystem (the
    FSPkg dummy package), one from vcs (initools) and one from an index
    (pip itself)::
    '''
    reset_env()
    fspkg = 'file://%s/FSPkg' %join(here, 'packages')
    dummy = run_pip('install', '-e', fspkg)
    pkg_lines = '''-e %s\n''' %fspkg
    pkg_lines = pkg_lines + """
-e svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev
pip"""
    write_file('bundle-req.txt', pkg_lines)
    result = run_pip('bundle', '-r', 'bundle-req.txt', 'test.pybundle')
    bundle = result.files_after.get('test.pybundle', None)
    assert bundle is not None
    files = zipfile.ZipFile(bundle.full).namelist()
    assert 'src/FSPkg/' in files
    assert 'src/initools/' in files
    assert 'build/pip/' in files

