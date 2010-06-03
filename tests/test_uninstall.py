
import textwrap
import sys
from os.path import join
from tempfile import mkdtemp
from test_pip import here, reset_env, run_pip, get_env, assert_all_changes, write_file
from path import Path
import pprint


def test_simple_uninstall():
    """
    Test simple install and uninstall.

    """
    env = reset_env()
    result = run_pip('install', 'INITools==0.2', expect_error=True)
    assert join(env.site_packages, 'initools') in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'INITools', '-y', expect_error=True)
    assert_all_changes(result, result2, [env.venv/'build', 'cache'])


def test_uninstall_with_scripts():
    """
    Uninstall an easy_installed package with scripts.

    """
    env = reset_env()
    result = env.run('easy_install', 'PyLogo')
    easy_install_pth = env.site_packages/ 'easy-install.pth'
    pylogo = sys.platform == 'win32' and 'pylogo' or 'PyLogo'
    assert(pylogo in result.files_updated[easy_install_pth].bytes)
    result2 = run_pip('uninstall', 'pylogo', '-y', expect_error=True)
    assert_all_changes(result, result2, [env.venv/'build', 'cache'])


def test_uninstall_namespace_package():
    """
    Uninstall a distribution with a namespace package without clobbering
    the namespace and everything in it.

    """
    env = reset_env()
    result = run_pip('install', 'pd.requires==0.0.3', expect_error=True)
    assert join(env.site_packages, 'pd') in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'pd.find', '-y', expect_error=True)
    assert join(env.site_packages, 'pd') not in result2.files_deleted, sorted(result2.files_deleted.keys())
    assert join(env.site_packages, 'pd', 'find') in result2.files_deleted, sorted(result2.files_deleted.keys())


def test_uninstall_console_scripts():
    """
    Test uninstalling a package with more files (console_script entry points, extra directories).

    """
    env = reset_env()
    result = run_pip('install', 'virtualenv', expect_error=True)
    assert env.bin/'virtualenv'+env.exe in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'virtualenv', '-y', expect_error=True)
    assert_all_changes(result, result2, [env.venv/'build', 'cache'])


def test_uninstall_easy_installed_console_scripts():
    """
    Test uninstalling package with console_scripts that is easy_installed.

    """
    env = reset_env()
    result = env.run('easy_install', 'virtualenv')
    assert env.bin/'virtualenv'+env.exe in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'virtualenv', '-y')
    assert_all_changes(result, result2, [env.venv/'build', 'cache'])


def test_uninstall_editable_from_svn():
    """
    Test uninstalling an editable installation from svn.

    """
    env = reset_env()
    result = run_pip('install', '-e', 'svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev')
    result.assert_installed('INITools')
    result2 = run_pip('uninstall', '-y', 'initools')
    assert (env.venv/'src'/'initools' in result2.files_after), 'oh noes, pip deleted my sources!'
    assert_all_changes(result, result2, [env.venv/'src', env.venv/'build'])


def test_uninstall_editable_with_source_outside_venv():
    """
    Test uninstalling editable install from existing source outside the venv.

    """
    tmpdir = join(mkdtemp(), 'virtualenv')
    env = reset_env()
    result = env.run('hg', 'clone', 'http://bitbucket.org/ianb/virtualenv/', tmpdir)
    result2 = run_pip('install', '-e', tmpdir)
    assert (join(env.site_packages, 'virtualenv.egg-link') in result2.files_created), result2.files_created.keys()
    result3 = run_pip('uninstall', '-y', 'virtualenv', expect_error=True)
    assert_all_changes(result, result3, [env.venv/'build'])


def test_uninstall_from_reqs_file():
    """
    Test uninstall from a requirements file.

    """
    env = reset_env()
    write_file('test-req.txt', textwrap.dedent("""\
        -e svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev
        # and something else to test out:
        PyLogo<0.4
        """))
    result = run_pip('install', '-r', 'test-req.txt')
    write_file('test-req.txt', textwrap.dedent("""\
        # -f, -i, and --extra-index-url should all be ignored by uninstall
        -f http://www.example.com
        -i http://www.example.com
        --extra-index-url http://www.example.com

        -e svn+http://svn.colorstudy.com/INITools/trunk#egg=initools-dev
        # and something else to test out:
        PyLogo<0.4
        """))
    result2 = run_pip('uninstall', '-r', 'test-req.txt', '-y')
    assert_all_changes(
        result, result2, [env.venv/'build', env.venv/'src', env.scratch/'test-req.txt'])
