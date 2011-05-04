import os.path
import textwrap
from pip.backwardcompat import urllib
from pip.req import Requirements
from tests.test_pip import reset_env, run_pip, write_file, pyversion, here, path_to_url
from tests.local_repos import local_checkout
from tests.path import Path


def test_requirements_file():
    """
    Test installing from a requirements file.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert env.site_packages/'INITools-0.2-py%s.egg-info' % pyversion in result.files_created
    assert env.site_packages/'initools' in result.files_created
    assert result.files_created[env.site_packages/other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[env.site_packages/fn].dir


def test_relative_requirements_file():
    """
    Test installing from a requirements file with a relative path with an egg= definition..

    """
    url = path_to_url(os.path.join(here, 'packages', '..', 'packages', 'FSPkg')) + '#egg=FSPkg'
    env = reset_env()
    write_file('file-egg-req.txt', textwrap.dedent("""\
        %s
        """ % url))
    result = run_pip('install', '-vvv', '-r', env.scratch_path / 'file-egg-req.txt')
    assert (env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)
    assert (env.site_packages/'fspkg') in result.files_created, str(result.stdout)


def test_multiple_requirements_files():
    """
    Test installing from multiple nested requirements files.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        -e %s@10#egg=INITools-dev
        -r %s-req.txt""" % (local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                            other_lib_name)))
    write_file('%s-req.txt' % other_lib_name, textwrap.dedent("""\
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = run_pip('install', '-r', env.scratch_path / 'initools-req.txt')
    assert result.files_created[env.site_packages/other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[env.site_packages/fn].dir
    assert env.venv/'src'/'initools' in result.files_created


def test_respect_order_in_requirements_file():
    env = reset_env()
    write_file('frameworks-req.txt', textwrap.dedent("""\
        bidict
        ordereddict
        mock
        """))
    result = run_pip('install', '-r', env.scratch_path / 'frameworks-req.txt')
    downloaded = [line for line in result.stdout.split('\n')
                  if 'Downloading/unpacking' in line]

    assert 'bidict' in downloaded[0], 'First download should ' \
            'be "bidict" but was "%s"' % downloaded[0]
    assert 'ordereddict' in downloaded[1], 'Second download should ' \
            'be "ordereddict" but was "%s"' % downloaded[1]
    assert 'mock' in downloaded[2], 'Third download should ' \
            'be "mock" but was "%s"' % downloaded[2]


def test_requirements_data_structure_keeps_order():
    requirements = Requirements()
    requirements['pip'] = 'pip'
    requirements['nose'] = 'nose'
    requirements['coverage'] = 'coverage'

    assert ['pip', 'nose', 'coverage'] == list(requirements.values())
    assert ['pip', 'nose', 'coverage'] == list(requirements.keys())


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
