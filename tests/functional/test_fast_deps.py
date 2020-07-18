import fnmatch
import json
from os.path import basename

from pip._vendor.packaging.utils import canonicalize_name
from pytest import mark


def pip(script, command, requirement):
    return script.pip(
        command, '--prefer-binary', '--no-cache-dir',
        '--use-feature=fast-deps', requirement,
        allow_stderr_warning=True,
    )


def assert_installed(script, names):
    list_output = json.loads(script.pip('list', '--format=json').stdout)
    installed = {canonicalize_name(item['name']) for item in list_output}
    assert installed.issuperset(map(canonicalize_name, names))


@mark.network
@mark.parametrize(('requirement', 'expected'), (
    ('Paste==3.4.2', ('Paste', 'six')),
    ('Paste[flup]==3.4.2', ('Paste', 'six', 'flup')),
))
def test_install_from_pypi(requirement, expected, script):
    pip(script, 'install', requirement)
    assert_installed(script, expected)


@mark.network
@mark.parametrize(('requirement', 'expected'), (
    ('Paste==3.4.2', ('Paste-3.4.2-*.whl', 'six-*.whl')),
    ('Paste[flup]==3.4.2', ('Paste-3.4.2-*.whl', 'six-*.whl', 'flup-*')),
))
def test_download_from_pypi(requirement, expected, script):
    result = pip(script, 'download', requirement)
    created = list(map(basename, result.files_created))
    assert all(fnmatch.filter(created, f) for f in expected)


@mark.network
def test_build_wheel_with_deps(data, script):
    result = pip(script, 'wheel', data.packages/'requiresPaste')
    created = list(map(basename, result.files_created))
    assert fnmatch.filter(created, 'requiresPaste-3.1.4-*.whl')
    assert fnmatch.filter(created, 'Paste-3.4.2-*.whl')
    assert fnmatch.filter(created, 'six-*.whl')
