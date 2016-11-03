import json
import os
import pytest

WARN_FORMAT = ("DEPRECATION: The default format will switch to columns in the "
               "future. You can use --format=(legacy|columns) (or define a "
               "format=(legacy|columns) in your pip.conf under the [list] "
               "section) to disable this warning.")


def test_list_command(script, data):
    """
    Test default behavior of list command without format specifier.
    A warning is expected.

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', expect_stderr=True)
    assert WARN_FORMAT in result.stderr, str(result)
    assert 'simple (1.0)' in result.stdout, str(result)
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_columns_flag(script, data):
    """
    Test the list command with the '--format=columns' option
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_legacy_format(script, data):
    """
    Test that legacy format
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=legacy')
    assert 'simple (1.0)' in result.stdout, str(result)
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_format_priority(script, data):
    """
    Test that latest format has priority over previous ones.
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=columns', '--format=legacy')
    assert 'simple (1.0)' in result.stdout, str(result)
    assert 'simple2 (3.0)' in result.stdout, str(result)
    assert 'simple     1.0' not in result.stdout, str(result)
    assert 'simple2    3.0' not in result.stdout, str(result)

    result = script.pip('list', '--format=legacy', '--format=columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert 'simple2 (3.0)' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_local_flag(script, data):
    """
    Test the behavior of --local flag in the list command

    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--format=legacy')
    assert 'simple (1.0)' in result.stdout


def test_local_columns_flag(script, data):
    """
    Test the behavior of --local --format=columns flags in the list command

    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple (1.0)' not in result.stdout
    assert 'simple     1.0' in result.stdout, str(result)


def test_local_legacy_flag(script, data):
    """
    Test the behavior of --local --format=legacy flags in the list
    command.
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--format=legacy')
    assert 'simple (1.0)' in result.stdout


def test_user_flag(script, data, virtualenv):
    """
    Test the behavior of --user flag in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--format=legacy')
    assert 'simple (1.0)' not in result.stdout
    assert 'simple2 (2.0)' in result.stdout


def test_user_columns_flag(script, data, virtualenv):
    """
    Test the behavior of --user --format=columns flags in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple2 (2.0)' not in result.stdout
    assert 'simple2 2.0' in result.stdout, str(result)


def test_user_legacy(script, data, virtualenv):
    """
    Test the behavior of --user flag in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--format=legacy')
    assert 'simple (1.0)' not in result.stdout
    assert 'simple2 (2.0)' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_flag(script, data):
    """
    Test the behavior of --uptodate flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--uptodate',
        '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout  # 3.0 is latest
    assert 'pip-test-package (0.1.1,' in result.stdout  # editables included
    assert 'simple2 (3.0)' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_columns_flag(script, data):
    """
    Test the behavior of --uptodate --format=columns flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--uptodate',
        '--format=columns',
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout      # editables included
    assert 'pip-test-package (0.1.1,' not in result.stdout
    assert 'pip-test-package 0.1.1' in result.stdout, str(result)
    assert 'simple2          3.0' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_legacy_flag(script, data):
    """
    Test the behavior of --uptodate --format=legacy flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--uptodate',
        '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout  # 3.0 is latest
    assert 'pip-test-package (0.1.1,' in result.stdout  # editables included
    assert 'simple2 (3.0)' in result.stdout, str(result)


@pytest.mark.network
def test_outdated_flag(script, data):
    """
    Test the behavior of --outdated flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0', 'simplewheel==1.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--outdated',
        '--format=legacy',
    )
    assert 'simple (1.0) - Latest: 3.0 [sdist]' in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' in result.stdout
    assert 'pip-test-package (0.1, ' in result.stdout
    assert ' Latest: 0.1.1 [sdist]' in result.stdout
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_outdated_columns_flag(script, data):
    """
    Test the behavior of --outdated --format=columns flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0', 'simplewheel==1.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--outdated',
        '--format=columns',
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Latest' in result.stdout
    assert 'Type' in result.stdout
    assert 'simple (1.0) - Latest: 3.0 [sdist]' not in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' not in result.stdout
    assert 'simple           1.0     3.0    sdist' in result.stdout, (
        str(result)
    )
    assert 'simplewheel      1.0     2.0    wheel' in result.stdout, (
        str(result)
    )
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_outdated_legacy(script, data):
    """
    Test the behavior of --outdated --format=legacy flag in the list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0', 'simplewheel==1.0',
    )
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--outdated',
        '--format=legacy',
    )
    assert 'simple (1.0) - Latest: 3.0 [sdist]' in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' in result.stdout
    assert 'pip-test-package (0.1, ' in result.stdout
    assert ' Latest: 0.1.1 [sdist]' in result.stdout
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_editables_flag(script, data):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip('list', '--editable', '--format=legacy')
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_editables_columns_flag(script, data):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip('list', '--editable', '--format=columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_editables_legacy(script, data):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '--editable', '--format=legacy', expect_stderr=True,
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_flag(script, data):
    """
    test the behavior of --editable --uptodate flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--uptodate',
        '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_columns_flag(script, data):
    """
    test the behavior of --editable --uptodate --format=columns flag in the
    list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--uptodate', '--format=columns',
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_legacy(script, data):
    """
    test the behavior of --editable --uptodate --format=columns --format=legacy
    flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index', '--editable',
        '--uptodate', '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_flag(script, data):
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--outdated',
        '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_columns_flag(script, data):
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--outdated', '--format=columns',
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_legacy(script, data):
    """
    test the behavior of --editable --outdated flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git'
        '@0.1#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--outdated', '--format=legacy',
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


def test_outdated_pre(script, data):
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path,
        '--format=legacy',
    )
    assert 'simple (1.0)' in result.stdout
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path, '--outdated',
        '--format=legacy',
    )
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout
    result_pre = script.pip('list', '--no-index',
                            '--find-links', wheelhouse_path,
                            '--outdated', '--pre', '--format=legacy')
    assert 'simple (1.0) - Latest: 2.0.dev0 [wheel]' in result_pre.stdout


def test_outdated_formats(script, data):
    """ Test of different outdated formats """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path,
        '--format=freeze',
    )
    assert 'simple==1.0' in result.stdout

    # Check legacy
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path,
                        '--outdated', '--format=legacy')
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout

    # Check columns
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path,
        '--outdated', '--format=columns',
    )
    assert 'Package Version Latest Type' in result.stdout
    assert 'simple  1.0     1.1    wheel' in result.stdout

    # Check freeze
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path,
        '--outdated', '--format=freeze',
    )
    assert 'simple==1.0' in result.stdout

    # Check json
    result = script.pip(
        'list', '--no-index', '--find-links', wheelhouse_path,
        '--outdated', '--format=json',
    )
    data = json.loads(result.stdout)
    assert data == [{'name': 'simple', 'version': '1.0',
                     'latest_version': '1.1', 'latest_filetype': 'wheel'}]


def test_not_required_flag(script, data):
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'TopoRequires4'
    )
    result = script.pip('list', '--not-required', expect_stderr=True)
    assert 'TopoRequires4 ' in result.stdout, str(result)
    assert 'TopoRequires ' not in result.stdout
    assert 'TopoRequires2 ' not in result.stdout
    assert 'TopoRequires3 ' not in result.stdout


def test_list_freeze(script, data):
    """
    Test freeze formatting of list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=freeze')
    assert 'simple==1.0' in result.stdout, str(result)
    assert 'simple2==3.0' in result.stdout, str(result)


def test_list_json(script, data):
    """
    Test json formatting of list command

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--format=json')
    data = json.loads(result.stdout)
    assert {'name': 'simple', 'version': '1.0'} in data
    assert {'name': 'simple2', 'version': '3.0'} in data
