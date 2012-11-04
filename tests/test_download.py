import textwrap
from tests.test_pip import reset_env, run_pip, write_file
from tests.path import Path


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


def test_download_should_download_dependencies():
    """
    It should download dependencies (in the scratch path)
    """

    env = reset_env()
    result = run_pip('install', 'Paste[openid]==1.7.5.1', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'Paste-1.7.5.1.tar.gz' in result.files_created
    openid_tarball_prefix = str(Path('scratch')/ 'python-openid-')
    assert any(path.startswith(openid_tarball_prefix) for path in result.files_created)
    assert env.site_packages/ 'openid' not in result.files_created


def test_download_should_skip_existing_files():
    """
    It should not download files already existing in the scratch dir
    """
    env = reset_env()

    write_file('test-req.txt', textwrap.dedent("""
        INITools==0.1
        """))

    result = run_pip('install', '-r', env.scratch_path/ 'test-req.txt', '-d', '.', expect_error=True)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created

    # adding second package to test-req.txt
    write_file('test-req.txt', textwrap.dedent("""
        INITools==0.1
        python-openid==2.2.5
        """))

    # only the second package should be downloaded
    result = run_pip('install', '-r', env.scratch_path/ 'test-req.txt', '-d', '.', expect_error=True)
    openid_tarball_prefix = str(Path('scratch')/ 'python-openid-')
    assert any(path.startswith(openid_tarball_prefix) for path in result.files_created)
    assert Path('scratch')/ 'INITools-0.1.tar.gz' not in result.files_created
    assert env.site_packages/ 'initools' not in result.files_created
    assert env.site_packages/ 'openid' not in result.files_created
