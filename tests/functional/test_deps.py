# -*- coding: utf-8 -*-

from tests.lib import path_to_url


def run_local_deps(script, *args, **kwargs):
    find_links = path_to_url('tests/data/packages/deps/')
    return run_deps(script, '-f', find_links, *args, **kwargs)

def run_deps(script, *args, **kwargs):
    kwargs['expect_stderr'] = True
    return script.pip('deps', '--no-index', *args, **kwargs)

def assert_result_contains(result, dependencies):
    if not isinstance(dependencies, (list, tuple)):
        dependencies = tuple(dependencies)

    for dependency in dependencies:
        assert dependency in result.stdout, \
            'Dependency "{0}" should be in stdout'.format(dependency)

    assert not result.files_created, 'Downloaded files should be removed'


def test_non_dependant_package(script):
    result = run_local_deps(script, 'dependency')
    assert_result_contains(result, 'dependency==1.0')

def test_single_dependency(script):
    result = run_local_deps(script, 'dependant')
    assert_result_contains(result, ['dependency==1.0', 'dependant==1.0'])

def test_url_dependency(script):
    url = path_to_url('tests/data/packages/deps/dependency-1.0.tar.gz')
    result = run_deps(script, url)
    assert_result_contains(result, url)

def test_dependency_links(script):
    result = run_local_deps(script, 'dependency-links')
    assert_result_contains(result, [
        'dependency-links==1.0',
        '--find-links http://pypi.python.org/simple'])
