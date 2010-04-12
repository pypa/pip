from os import makedirs
from os.path import join
import textwrap
from test_pip import here, reset_env, run_pip, pyversion, lib_py, get_env, diff_states, write_file

def test_download_if_requested():
    """
    It should download and not install if requested.
    
    """
    reset_env()
    result = run_pip('install', 'INITools==0.1', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created

def test_single_download_from_requirements_file():
    """
    It should support download from PyPi from a requirements file"
    """
    reset_env()
    write_file('test-req.txt', textwrap.dedent("""
        INITools==0.1
        """))
    result = run_pip('install', '-r', env.base_path/ 'test-req.txt', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created
