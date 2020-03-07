import os
from glob import glob

import pytest


@pytest.fixture
def cache_dir(script):
    result = script.run(
        'python', '-c',
        'from pip._internal.locations import USER_CACHE_DIR;'
        'print(USER_CACHE_DIR)'
    )
    return result.stdout.strip()


@pytest.fixture
def wheel_cache_dir(cache_dir):
    return os.path.normcase(os.path.join(cache_dir, 'wheels'))


@pytest.fixture
def wheel_cache_files(wheel_cache_dir):
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    filenames = glob(os.path.join(destination, '*.whl'))
    files = []
    for filename in filenames:
        files.append(os.path.join(destination, filename))
    return files


@pytest.fixture
def populate_wheel_cache(wheel_cache_dir):
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    os.makedirs(destination)

    files = [
        ('yyy-1.2.3', os.path.join(destination, 'yyy-1.2.3-py3-none-any.whl')),
        ('zzz-4.5.6', os.path.join(destination, 'zzz-4.5.6-py3-none-any.whl')),
    ]

    for _name, filename in files:
        with open(filename, 'w'):
            pass

    return files


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_info(script, wheel_cache_dir, wheel_cache_files):
    result = script.pip('cache', 'info')

    assert 'Location: {}'.format(wheel_cache_dir) in result.stdout
    num_wheels = len(wheel_cache_files)
    assert 'Number of wheels: {}'.format(num_wheels) in result.stdout


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list(script):
    result = script.pip('cache', 'list')

    assert 'yyy-1.2.3' in result.stdout
    assert 'zzz-4.5.6' in result.stdout


def test_cache_list_too_many_args(script):
    script.pip('cache', 'list', 'aaa', 'bbb',
               expect_error=True)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_list_with_pattern(script):
    result = script.pip('cache', 'list', 'zzz')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_remove(script):
    script.pip('cache', 'remove', expect_error=True)
    result = script.pip('cache', 'remove', 'zzz', '--verbose')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout


def test_cache_remove_too_many_args(script):
    script.pip('cache', 'remove', 'aaa', 'bbb',
               expect_error=True)


@pytest.mark.usefixtures("populate_wheel_cache")
def test_cache_purge(script):
    result = script.pip('cache', 'purge', 'aaa', '--verbose',
                        expect_error=True)
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' not in result.stdout

    result = script.pip('cache', 'purge', '--verbose')
    assert 'yyy-1.2.3' in result.stdout
    assert 'zzz-4.5.6' in result.stdout
