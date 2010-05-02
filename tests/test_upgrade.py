
from os.path import join
import textwrap
from test_pip import here, reset_env, run_pip, get_env, diff_states, write_file

def test_no_upgrade_unless_requested():
    """
    No upgrade if not specifically requested.

    """
    reset_env()
    result = run_pip('install', 'INITools==0.1', expect_error=True)
    result2 = run_pip('install', 'INITools', expect_error=True)
    assert not result2.files_created, 'pip install INITools upgraded when it should not have'

def test_upgrade_to_specific_version():
    """
    It does upgrade to specific version requested.

    """
    reset_env()
    result = run_pip('install', 'INITools==0.1', expect_error=True)
    result2 = run_pip('install', 'INITools==0.2', expect_error=True)
    assert result2.files_created, 'pip install with specific version did not upgrade'

def test_upgrade_if_requested():
    """
    And it does upgrade if requested.

    """
    reset_env()
    result = run_pip('install', 'INITools==0.1', expect_error=True)
    result2 = run_pip('install', '--upgrade', 'INITools', expect_error=True)
    assert result2.files_created, 'pip install --upgrade did not upgrade'

def test_uninstall_before_upgrade():
    """
    Automatic uninstall-before-upgrade.

    """
    env = reset_env()
    result = run_pip('install', 'INITools==0.2', expect_error=True)
    assert env.site_packages/ 'initools' in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('install', 'INITools==0.3', expect_error=True)
    assert result2.files_created, 'upgrade to INITools 0.3 failed'
    result3 = run_pip('uninstall', 'initools', '-y', expect_error=True)
    assert diff_states(result.files_before, result3.files_after, ignore=['env/build', 'cache']).values() == [{}, {}, {}]

def test_upgrade_from_reqs_file():
    """
    Upgrade from a requirements file.

    """
    env = reset_env()
    write_file('test-req.txt', textwrap.dedent("""\
        PyLogo<0.4
        # and something else to test out:
        INITools==0.3
        """))
    result = run_pip('install', '-r', env.scratch_path/ 'test-req.txt')
    write_file('test-req.txt', textwrap.dedent("""\
        PyLogo
        # and something else to test out:
        INITools
        """))
    result2 = run_pip('install', '--upgrade', '-r', env.scratch_path/ 'test-req.txt')
    result3 = run_pip('uninstall', '-r', env.scratch_path/ 'test-req.txt', '-y')
    res = diff_states(result.files_before, result3.files_after, ignore=['env/build', 'cache', 'scratch/test-req.txt']).values() 
    assert res == [{}, {}, {}], res

def test_uninstall_rollback():
    """
    Test uninstall-rollback (using test package with a setup.py
    crafted to fail on install).

    """
    env = reset_env()
    find_links = 'file://' + join(here, 'packages')
    result = run_pip('install', '-f', find_links, '--no-index', 'broken==0.1')
    assert env.site_packages / 'broken.py' in result.files_created, result.files_created.keys()
    result2 = run_pip('install', '-f', find_links, '--no-index', 'broken==0.2broken', expect_error=True)
    assert result2.returncode == 1, str(result2)
    env.run( 'python', '-c', "import broken; print broken.VERSION").stdout
    '0.1\n'
    assert diff_states(result.files_after, result2.files_after, ignore=[env.venv/'build', 'pip-log.txt']).values() == [{}, {}, {}]
