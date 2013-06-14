from os.path import abspath, join

from nose import SkipTest
from tests.lib import tests_data, reset_env, run_pip, pip_install_local, find_links
from tests.lib.path import Path


def test_install_from_wheel():
    """
    Test installing from a wheel.
    """
    env = reset_env()
    result = run_pip('install', 'simple.dist', '--use-wheel',
                     '--no-index', '--find-links='+find_links,
                     expect_error=False)
    dist_info_folder = env.site_packages/'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_install_from_wheel_with_extras():
    """
    Test installing from a wheel with extras.
    """
    try:
        import ast
    except ImportError:
        raise SkipTest("Need ast module to interpret wheel extras")
    env = reset_env()
    result = run_pip('install', 'complex-dist[simple]', '--use-wheel',
                     '--no-index', '--find-links='+find_links,
                     expect_error=False)
    dist_info_folder = env.site_packages/'complex_dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    dist_info_folder = env.site_packages/'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_install_from_wheel_file():
    """
    Test installing directly from a wheel file.
    """
    env = reset_env()
    package = abspath(join(tests_data,
                           'packages',
                           'headers.dist-0.1-py2.py3-none-any.whl'))
    result = run_pip('install', package, '--no-index', expect_error=False)
    dist_info_folder = env.site_packages/'headers.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_install_wheel_with_target():
    """
    Test installing a wheel using pip install --target
    """
    env = reset_env()
    pip_install_local('wheel')
    target_dir = env.scratch_path/'target'
    result = run_pip('install', 'simple.dist==0.1', '-t', target_dir, '--use-wheel',
                     '--no-index', '--find-links='+find_links)
    assert Path('scratch')/'target'/'simpledist' in result.files_created, str(result)


def test_install_from_wheel_installs_deps():
    """
    Test can install dependencies of wheels
    """
    # 'requires_source' depends on the 'source' project
    env = reset_env()
    package = abspath(join(tests_data,
                           'packages',
                           'requires_source-1.0-py2.py3-none-any.whl'))
    result = run_pip('install', '--no-index', '--find-links', find_links, package)
    result.assert_installed('source', editable=False)


def test_install_from_wheel_no_deps():
    """
    Test --no-deps works with wheel installs
    """
    # 'requires_source' depends on the 'source' project
    env = reset_env()
    package = abspath(join(tests_data,
                           'packages',
                           'requires_source-1.0-py2.py3-none-any.whl'))
    result = run_pip('install', '--no-index', '--find-links', find_links, '--no-deps', package)
    pkg_folder = env.site_packages/'source'
    assert pkg_folder not in result.files_created



