import os
import pytest

from pip.exceptions import CommandError


def test_list_command(script, data):
    """
    Test default behavior of list command.

    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list')
    assert 'simple (1.0)' in result.stdout, str(result)
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_columns_flag(script, data):
    """
    Test the list command with the '--columns' option
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--columns')
    assert 'Package' in result.stdout, str(result)
    assert 'Version' in result.stdout, str(result)
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)
    assert 'simple2    3.0' in result.stdout, str(result)


def test_columns_noheader_flag(script, data):
    """
    Test the list command with the '--columns' and '--no-header' option
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--columns', '--no-header')
    assert 'Package' not in result.stdout, str(result)
    assert 'Version' not in result.stdout, str(result)
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert 'simple     1.0' in result.stdout, str(result)


def test_noheader_flag(script, data):
    """
    Test the list command with the '--no-header' option but not the `--columns`
    option raises an error.
    """
    script.pip(
        'install', '-f', data.find_links, '--no-index', 'simple==1.0',
        'simple2==3.0',
    )
    result = script.pip('list', '--no-header')
    assert 'Option --no-header can only be' in result.stderr, str(result)


def test_local_flag(script, data):
    """
    Test the behavior of --local flag in the list command

    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local')
    assert 'simple (1.0)' in result.stdout


def test_local_columns_flag(script, data):
    """
    Test the behavior of --local --columns flags in the list command

    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple (1.0)' not in result.stdout
    assert 'simple     1.0' in result.stdout, str(result)


def test_local_columns_noheader_flag(script, data):
    """
    Test the behavior of --local --columns --no-header flags in the list
    command.
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--columns', '--no-header')
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'simple (1.0)' not in result.stdout
    assert 'simple     1.0' in result.stdout, str(result)


def test_local_noheader_flag(script, data):
    """
    Test the behavior of --local --no-header flags in the list
    command.
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local', '--no-header')
    assert 'Option --no-header can only be' in result.stderr, str(result)


def test_user_flag(script, data, virtualenv):
    """
    Test the behavior of --user flag in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user')
    assert 'simple (1.0)' not in result.stdout
    assert 'simple2 (2.0)' in result.stdout, str(result)


def test_user_columns_flag(script, data, virtualenv):
    """
    Test the behavior of --user --columns flags in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'simple2 (2.0)' not in result.stdout
    assert 'simple2 2.0' in result.stdout, str(result)


def test_user_columns_noheader_flag(script, data, virtualenv):
    """
    Test the behavior of --user --columns --no-header flags in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--columns', '--no-header')
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'simple2 (2.0)' not in result.stdout
    assert 'simple2 2.0' in result.stdout, str(result)


def test_user_noheader_flag(script, data, virtualenv):
    """
    Test the behavior of --user flag in the list command

    """
    virtualenv.system_site_packages = True
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip('install', '-f', data.find_links, '--no-index',
               '--user', 'simple2==2.0')
    result = script.pip('list', '--user', '--no-header')
    assert 'Option --no-header can only be' in result.stderr, str(result)


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
        expect_stderr=True,
    )
    assert 'simple (1.0)' not in result.stdout  # 3.0 is latest
    assert 'pip-test-package (0.1.1,' in result.stdout  # editables included
    assert 'simple2 (3.0)' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_columns_flag(script, data):
    """
    Test the behavior of --uptodate --columns flag in the list command

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
        'list', '-f', data.find_links, '--no-index', '--uptodate', '--columns',
        expect_stderr=True,
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout      # editables included
    assert 'pip-test-package (0.1.1,' not in result.stdout
    assert 'pip-test-package 0.1.1' in result.stdout, str(result)
    assert 'simple2          3.0' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_columns_noheader_flag(script, data):
    """
    Test the behavior of --uptodate --columns --noheader flag in the
    list command
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
        'list', '-f', data.find_links, '--no-index', '--uptodate', '--columns',
        '--no-header', expect_stderr=True,
    )
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'Location' not in result.stdout      # editables included
    assert 'pip-test-package (0.1.1,' not in result.stdout
    assert 'pip-test-package 0.1.1,' in result.stdout
    assert 'simple2          3.0' in result.stdout, str(result)


@pytest.mark.network
def test_uptodate_noheader_flag(script, data):
    """
    Test the behavior of --uptodate --no-header flag in the list command

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
        '--no-header', expect_stderr=True,
    )
    assert 'Option --no-header can only be' in result.stderr, str(result)


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
        expect_stderr=True,
    )
    assert 'simple (1.0) - Latest: 3.0 [sdist]' in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' in result.stdout
    assert 'pip-test-package (0.1, ' in result.stdout
    assert ' Latest: 0.1.1 [sdist]' in result.stdout
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_outdated_columns_flag(script, data):
    """
    Test the behavior of --outdated --columns flag in the list command

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
        '--columns', expect_stderr=True,
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Latest' in result.stdout
    assert 'Type' in result.stdout
    assert 'simple (1.0) - Latest: 3.0 [sdist]' not in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' not in result.stdout
    assert 'simple           1.0 3.0   sdist' in result.stdout, str(result)
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_outdated_columns_noheader_flag(script, data):
    """
    Test the behavior of --outdated --columns --no-header flag in the
    list command
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
        '--columns', '--noheader', expect_stderr=True,
    )
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'Latest' not in result.stdout
    assert 'Type' not in result.stdout
    assert 'simple (1.0) - Latest: 3.0 [sdist]' not in result.stdout
    assert 'simplewheel (1.0) - Latest: 2.0 [wheel]' not in result.stdout
    assert 'simple           1.0 3.0   sdist' in result.stdout, str(result)
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


@pytest.mark.network
def test_outdated_noheader_flag(script, data):
    """
    Test the behavior of --outdated --no-header flag in the list command

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
        '--noheader', expect_stderr=True,
    )
    assert 'Option --no-header can only be' in result.stderr, str(result)


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
    result = script.pip('list', '--editable')
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
    result = script.pip('list', '--editable', '--columns')
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_editables_columns_noheader_flag(script, data):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip('list', '--editable', '--columns', '--no-header')
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'Location' not in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_editables_noheader_flag(script, data):
    """
    Test the behavior of --editables flag in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip('list', '--editable', '--no-header')
    assert 'Option --no-header can only be' in result.stderr, str(result)


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
        expect_stderr=True,
    )
    assert 'simple (1.0)' not in result.stdout, str(result)
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_columns_flag(script, data):
    """
    test the behavior of --editable --uptodate --columns flag in the
    list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--uptodate', '--columns',
        expect_stderr=True,
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_columns_noheader_flag(script, data):
    """
    test the behavior of --editable --uptodate --columns --no-header flag
    in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--uptodate', '--columns', '--no-header',
        expect_stderr=True,
    )
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'Location' not in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_uptodate_editables_noheader_flag(script, data):
    """
    test the behavior of --editable --uptodate --columns --no-header flag
    in the list command
    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    script.pip(
        'install', '-e',
        'git+https://github.com/pypa/pip-test-package.git#egg=pip-test-package'
    )
    result = script.pip(
        'list', '-f', data.find_links, '--no-index',
        '--editable', '--uptodate', '--no-header',
        expect_stderr=True,
    )
    assert 'Option --no-header can only be' in result.stderr, str(result)


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
        expect_stderr=True,
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
        '--editable', '--outdated', '--columns',
        expect_stderr=True,
    )
    assert 'Package' in result.stdout
    assert 'Version' in result.stdout
    assert 'Location' in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_columns_noheader_flag(script, data):
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
        '--editable', '--outdated', '--columns', '--no-header',
        expect_stderr=True,
    )
    assert 'Package' not in result.stdout
    assert 'Version' not in result.stdout
    assert 'Location' not in result.stdout
    assert os.path.join('src', 'pip-test-package') in result.stdout, (
        str(result)
    )


@pytest.mark.network
def test_outdated_editables_noheader_flag(script, data):
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
        '--editable', '--outdated', '--no-header',
        expect_stderr=True,
    )
    assert 'Option --no-header can only be' in result.stderr, str(result)


def test_outdated_pre(script, data):
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path)
    assert 'simple (1.0)' in result.stdout
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path,
                        '--outdated')
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout
    result_pre = script.pip('list', '--no-index',
                            '--find-links', wheelhouse_path,
                            '--outdated', '--pre')
    assert 'simple (1.0) - Latest: 2.0.dev0 [wheel]' in result_pre.stdout


def test_outdated_pre_columns(script, data):
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path)
    assert 'simple (1.0)' in result.stdout
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path,
                        '--outdated')
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout
    result_pre = script.pip('list', '--no-index',
                            '--find-links', wheelhouse_path,
                            '--outdated', '--pre', '--columns')
    assert 'Package' in result_pre.stdout
    assert 'Version' in result_pre.stdout
    assert 'Latest' in result_pre.stdout
    assert 'Type' in result_pre.stdout


def test_outdated_pre_columns_noheader(script, data):
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path)
    assert 'simple (1.0)' in result.stdout
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path,
                        '--outdated')
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout
    result_pre = script.pip('list', '--no-index',
                            '--find-links', wheelhouse_path,
                            '--outdated', '--pre', '--columns', '--no-header')
    assert 'Package' not in result_pre.stdout
    assert 'Version' not in result_pre.stdout
    assert 'Latest' not in result_pre.stdout
    assert 'Type' not in result_pre.stdout


def test_outdated_pre_noheader(script, data):
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')

    # Let's build a fake wheelhouse
    script.scratch_path.join("wheelhouse").mkdir()
    wheelhouse_path = script.scratch_path / 'wheelhouse'
    wheelhouse_path.join('simple-1.1-py2.py3-none-any.whl').write('')
    wheelhouse_path.join('simple-2.0.dev0-py2.py3-none-any.whl').write('')
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path)
    assert 'simple (1.0)' in result.stdout
    result = script.pip('list', '--no-index', '--find-links', wheelhouse_path,
                        '--outdated')
    assert 'simple (1.0) - Latest: 1.1 [wheel]' in result.stdout
    result = script.pip('list', '--no-index',
        '--find-links', wheelhouse_path,
        '--outdated', '--pre', '--no-header',
    )
    assert 'Option --no-header can only be' in result.stderr, str(result)
