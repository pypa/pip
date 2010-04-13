
import os
import textwrap
from test_pip import reset_env, run_pip, write_file

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
    result = run_pip('install', '-r', env.base_path / 'initools-req.txt')
    assert len(result.wildcard_matches('env/lib/python*/site-packages/INITools-0.2-py*.egg-info')) == 1
    assert len(result.wildcard_matches('env/lib/python*/site-packages/initools')) == 1
    dirs = result.wildcard_matches('env/lib/python*/site-packages/simplejson*')
    assert len(dirs) == 2
    assert dirs[0].dir, dirs[1].dir == (True, True)

def test_multiple_requirements_files():
    """
    Test installing from multiple nested requirements files.
    
    """
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        -e svn+http://svn.colorstudy.com/INITools/trunk@3139#egg=INITools-dev
        -r simplejson-req.txt"""))
    write_file('simplejson-req.txt', textwrap.dedent("""\
        simplejson<=1.7.4
        """))
    result = run_pip('install', '-r', env.base_path / 'initools-req.txt')
    assert len(result.wildcard_matches('env/lib/python*/site-packages/simplejson*')) == 2
    assert 'env/src/initools' in result.files_created

