from os import makedirs
from os.path import join
import textwrap
from test_pip import here, reset_env, run_pip, pyversion, write_file
from path import Path


def test_download_if_requested():
    """
    It should download (in the scratch path) and not install if requested.
    """

    env = reset_env()
    result = run_pip('install', 'INITools==0.1', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created


def test_single_download_from_requirements_file():
    """
    It should support download (in the scratch path) from PyPi from a requirements file
    """

    env = reset_env()
    write_file('test-req.txt', textwrap.dedent("""
        INITools==0.1
        """))
    result = run_pip('install', '-r', env.scratch_path/ 'test-req.txt', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created
