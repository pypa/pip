import textwrap

from tests.test_pip import reset_env, run_pip, pyversion, here, write_file


def test_find_links_relative_path():
    """Test find-links as a relative path."""
    e = reset_env()
    result = run_pip(
        'install',
        'parent==0.1',
        '--no-index',
        '--find-links',
        'packages/',
        cwd=here)
    egg_info_folder = e.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_find_links_requirements_file_relative_path():
    """Test find-links as a relative path to a reqs file."""
    e = reset_env()
    write_file('test-req.txt', textwrap.dedent("""
        --no-index
        --find-links=../../../packages/
        parent==0.1
        """))
    result = run_pip(
        'install',
        '-r',
        e.scratch_path / "test-req.txt",
        cwd=here)
    egg_info_folder = e.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)
