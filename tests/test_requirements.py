import textwrap
from pip.req import Requirements
from test_pip import reset_env, run_pip, write_file, pyversion
from local_repos import local_checkout


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
        -e %s@10#egg=INITools-dev
        -r simplejson-req.txt""" % local_checkout('http://svn.colorstudy.com/INITools/trunk')))
    write_file('simplejson-req.txt', textwrap.dedent("""\
        simplejson<=1.7.4
        """))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert result.files_created[env.site_packages/'simplejson'].dir
    assert result.files_created[env.site_packages/'simplejson-1.7.4-py%s.egg-info' % pyversion].dir
    assert env.venv/'src'/'initools' in result.files_created


def test_respect_order_in_requirements_file():
    env = reset_env()
    write_file('frameworks-req.txt', textwrap.dedent("""\
        coverage
        ordereddict
        bottle
        """))
    result = run_pip('install', '-r', env.scratch_path / 'frameworks-req.txt')
    downloaded = [line for line in result.stdout.split('\n')
                  if 'Downloading/unpacking' in line]
    
    assert 'coverage' in downloaded[0], 'First download should ' \
            'be "coverage" but was "%s"' % downloaded[0] 
    assert 'ordereddict' in downloaded[1], 'Second download should ' \
            'be "ordereddict" but was "%s"' % downloaded[1]
    assert 'bottle' in downloaded[2], 'Third download should ' \
            'be "bottle" but was "%s"' % downloaded[2]


def test_requirements_data_structure_keeps_order():
    requirements = Requirements()
    requirements['pip'] = 'pip'
    requirements['nose'] = 'nose'
    requirements['coverage'] = 'coverage'

    assert ['pip', 'nose', 'coverage'] == requirements.values()
    assert ['pip', 'nose', 'coverage'] == requirements.keys()

def test_requirements_data_structure_implements__repr__():
    requirements = Requirements()
    requirements['pip'] = 'pip'
    requirements['nose'] = 'nose'

    assert "Requirements({'pip': 'pip', 'nose': 'nose'})" == repr(requirements)

def test_requirements_data_structure_implements__contains__():
    requirements = Requirements()
    requirements['pip'] = 'pip'

    assert 'pip' in requirements
    assert 'nose' not in requirements
