import os
import shutil


def _cache_dir(script):
    result = script.run(
        'python', '-c',
        'from pip._internal.locations import USER_CACHE_DIR;'
        'print(USER_CACHE_DIR)'
    )
    return result.stdout.strip()


def _wheel_cache_contents(script):
    cache_dir = _cache_dir(script)
    wheel_cache_dir = os.path.join(cache_dir, 'wheels')
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    os.makedirs(destination)

    files = [
        ('yyy-1.2.3', os.path.join(destination, 'yyy-1.2.3-py3-none-any.whl')),
        ('zzz-4.5.6', os.path.join(destination, 'zzz-4.5.6-py27-none-any.whl')),
    ]

    for _name, filename in files:
        with open(filename, 'w'):
            pass

    return files


def test_cache_info(script):
    cache_dir = _cache_dir(script)
    cache_files = _wheel_cache_contents(script)

    result = script.pip('cache', 'info')

    assert 'Location: {}'.format(os.path.normcase(cache_dir)) in result.stdout
    assert 'Number of wheels: {}'.format(len(cache_files)) in result.stdout


def test_cache_list(script):
    cache_files = _wheel_cache_contents(script)
    packages = [name for (name, _path) in cache_files]
    result = script.pip('cache', 'list')
    for package in packages:
        assert package in result.stdout
    # assert 'yyy-1.2.3' in result.stdout
    # assert 'zzz-4.5.6' in result.stdout


def test_cache_list_too_many_args(script):
    script.pip('cache', 'list', 'aaa', 'bbb',
               expect_error=True)


def test_cache_list_with_pattern(script):
    cache_files = _wheel_cache_contents(script)

    result = script.pip('cache', 'list', 'zzz')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout


def test_cache_remove(script, monkeypatch):
    cache_files = _wheel_cache_contents(script)

    script.pip('cache', 'remove', expect_error=True)
    result = script.pip('cache', 'remove', 'zzz', '--verbose')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout


def test_cache_remove_too_many_args(script):
    script.pip('cache', 'remove', 'aaa', 'bbb',
               expect_error=True)


def test_cache_purge(script):
    cache_files = _wheel_cache_contents(script)

    result = script.pip('cache', 'purge', 'aaa', '--verbose',
                        expect_error=True)
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' not in result.stdout

    result = script.pip('cache', 'purge', '--verbose')
    assert 'yyy-1.2.3' in result.stdout
    assert 'zzz-4.5.6' in result.stdout
