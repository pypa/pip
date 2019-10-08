import os
import shutil


def _cache_dir(script):
    results = script.run(
        'python', '-c',
        'from pip._internal.locations import USER_CACHE_DIR;'
        'print(USER_CACHE_DIR)'
    )
    return str(results.stdout).strip()


def test_cache_info(script, monkeypatch):
    result = script.pip('cache', 'info')
    cache_dir = _cache_dir(script)

    assert 'Location: %s' % cache_dir in result.stdout
    assert 'Packages: ' in result.stdout


def test_cache_list(script, monkeypatch):
    cache_dir = _cache_dir(script)
    wheel_cache_dir = os.path.join(cache_dir, 'wheels')
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    os.makedirs(destination)
    with open(os.path.join(destination, 'yyy-1.2.3.whl'), 'w'):
        pass
    with open(os.path.join(destination, 'zzz-4.5.6.whl'), 'w'):
        pass
    result = script.pip('cache', 'list')
    assert 'yyy-1.2.3' in result.stdout
    assert 'zzz-4.5.6' in result.stdout
    shutil.rmtree(os.path.join(wheel_cache_dir, 'arbitrary'))


def test_cache_list_with_pattern(script, monkeypatch):
    cache_dir = _cache_dir(script)
    wheel_cache_dir = os.path.join(cache_dir, 'wheels')
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    os.makedirs(destination)
    with open(os.path.join(destination, 'yyy-1.2.3.whl'), 'w'):
        pass
    with open(os.path.join(destination, 'zzz-4.5.6.whl'), 'w'):
        pass
    result = script.pip('cache', 'list', 'zzz')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout
    shutil.rmtree(os.path.join(wheel_cache_dir, 'arbitrary'))


def test_cache_remove(script, monkeypatch):
    cache_dir = _cache_dir(script)
    wheel_cache_dir = os.path.join(cache_dir, 'wheels')
    destination = os.path.join(wheel_cache_dir, 'arbitrary', 'pathname')
    os.makedirs(destination)
    with open(os.path.join(wheel_cache_dir, 'yyy-1.2.3.whl'), 'w'):
        pass
    with open(os.path.join(wheel_cache_dir, 'zzz-4.5.6.whl'), 'w'):
        pass

    script.pip('cache', 'remove', expect_error=True)
    result = script.pip('cache', 'remove', 'zzz', '--verbose')
    assert 'yyy-1.2.3' not in result.stdout
    assert 'zzz-4.5.6' in result.stdout
    shutil.rmtree(os.path.join(wheel_cache_dir, 'arbitrary'))
