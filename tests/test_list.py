import os
import re
from tests.test_pip import reset_env, run_pip, path_to_url, here

find_links = path_to_url(os.path.join(here, 'packages'))

def test_list_command():
    """
    Test default behavior of list command.

    """
    reset_env()
    run_pip('install', '-f', find_links, '--no-index', 'simple==1.0', 'simple2==3.0')
    result = run_pip('list')
    assert 'simple (1.0)' in result.stdout, str(result)
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_output_formating():
    """
    Test the output formating in the list command

    """
    reset_env()
    run_pip('install', 'mock==0.7.0')
    result = run_pip('list', '--format', '{name} - {version}')
    assert 'mock - 0.7.0' in result.stdout


def test_local_flag():
    """
    Test the behavior of --local flag in the list command

    """
    reset_env()
    run_pip('install', '-f', find_links, '--no-index', 'simple==1.0')
    result = run_pip('list', '--local')
    assert 'simple (1.0)' in result.stdout


def test_uptodate_flag():
    """
    Test the behavior of --uptodate flag in the list command

    """
    reset_env()
    run_pip('install', '-f', find_links, '--no-index', 'simple==1.0', 'simple2==3.0')
    run_pip('install', '-e', 'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package')
    result = run_pip('list', '-f', find_links, '--no-index', '--uptodate')
    assert 'simple (1.0)' not in result.stdout #3.0 is latest
    assert 'pip-test-package' not in result.stdout #editables excluded
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_outdated_flag():
    """
    Test the behavior of --outdated flag in the list command

    """
    reset_env()
    run_pip('install', '-f', find_links, '--no-index', 'simple==1.0', 'simple2==3.0')
    run_pip('install', '-e', 'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package')
    result = run_pip('list', '-f', find_links, '--no-index', '--outdated')
    assert 'simple (Current: 1.0 Latest: 3.0)' in result.stdout
    assert 'pip-test-package' not in result.stdout #editables excluded
    assert 'simple2' not in result.stdout, str(result) #3.0 is latest


def test_output_formating_in_outdated_flag():
    """
    Test the output formating for --outdated flag in the list command

    """
    reset_env()
    run_pip('install', 'mock==0.7.0')
    total_re = re.compile('LATEST: +([0-9.\w]+)')
    result = run_pip('search', 'mock')
    mock_ver = total_re.search(str(result)).group(1)
    as_json = '{{"packageName": "{name}","current":"{version}","latest":"{version_raw}"}}'
    result = run_pip('list', '--outdated', '--format', as_json, expect_stderr=True)
    expected = '{"packageName": "mock","current":"0.7.0","latest":"%s"}' % mock_ver
    assert expected in result.stdout


def test_editables_flag():
    """
    Test the behavior of --editables flag in the list command
    """
    reset_env()
    run_pip('install', '-f', find_links, '--no-index', 'simple==1.0')
    result = run_pip('install', '-e', 'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package')
    result = run_pip('list', '--editable')
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, str(result)
