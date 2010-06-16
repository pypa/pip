import textwrap
from test_pip import reset_env, run_pip, write_file, pyversion
from local_repos import local_repo


def test_requirements_file():
    """
    Test installing from a requirements file.

    """
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        simplejson<=1.7.4
        """))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert env.site_packages/'INITools-0.2-py%s.egg-info' % pyversion in result.files_created
    assert env.site_packages/'initools' in result.files_created
    assert result.files_created[env.site_packages/'simplejson'].dir
    assert result.files_created[env.site_packages/'simplejson-1.7.4-py%s.egg-info' % pyversion].dir


def test_multiple_requirements_files():
    """
    Test installing from multiple nested requirements files.

    """
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        -e svn+%s@3139#egg=INITools-dev
        -r simplejson-req.txt""" % local_repo('http://svn.colorstudy.com/INITools/trunk')))
    write_file('simplejson-req.txt', textwrap.dedent("""\
        simplejson<=1.7.4
        """))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert result.files_created[env.site_packages/'simplejson'].dir
    assert result.files_created[env.site_packages/'simplejson-1.7.4-py%s.egg-info' % pyversion].dir
    assert env.venv/'src'/'initools' in result.files_created

