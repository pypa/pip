import os


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


def test_local_flag(script, data):
    """
    Test the behavior of --local flag in the list command

    """
    script.pip('install', '-f', data.find_links, '--no-index', 'simple==1.0')
    result = script.pip('list', '--local')
    assert 'simple (1.0)' in result.stdout


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
        'list', '-f', data.find_links, '--no-index', '--uptodate'
    )
    assert 'simple (1.0)' not in result.stdout  # 3.0 is latest
    assert 'pip-test-package' not in result.stdout  # editables excluded
    assert 'simple2 (3.0)' in result.stdout, str(result)


def test_outdated_flag(script, data):
    """
    Test the behavior of --outdated flag in the list command

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
        'list', '-f', data.find_links, '--no-index', '--outdated',
    )
    assert 'simple (Current: 1.0 Latest: 3.0)' in result.stdout
    assert 'pip-test-package' not in result.stdout  # editables excluded
    assert 'simple2' not in result.stdout, str(result)  # 3.0 is latest


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
