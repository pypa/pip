from pip._vendor import pytoml

from pip._internal.build_env import BuildEnvironment
from pip._internal.download import PipSession
from pip._internal.index import PackageFinder
from pip._internal.req import InstallRequirement
from tests.lib import path_to_url


def make_project(tmpdir, requires=[], backend=None):
    project_dir = (tmpdir / 'project').mkdir()
    buildsys = {'requires': requires}
    if backend:
        buildsys['build-backend'] = backend
    data = pytoml.dumps({'build-system': buildsys})
    project_dir.join('pyproject.toml').write(data)
    return project_dir


def test_backend(tmpdir, data):
    """Check we can call a requirement's backend successfully"""
    project_dir = make_project(tmpdir, backend="dummy_backend")
    req = InstallRequirement(None, None, source_dir=project_dir)
    req.load_pyproject_toml()
    env = BuildEnvironment()
    finder = PackageFinder([data.backends], [], session=PipSession())
    env.install_requirements(finder, ["dummy_backend"], 'normal', "Installing")
    conflicting, missing = env.check_requirements(["dummy_backend"])
    assert not conflicting and not missing
    assert hasattr(req.pep517_backend, 'build_wheel')
    with env:
        assert req.pep517_backend.build_wheel("dir") == "Backend called"


def test_pep517_install(script, tmpdir, data):
    """Check we can build with a custom backend"""
    project_dir = make_project(
        tmpdir, requires=['test_backend'],
        backend="test_backend"
    )
    result = script.pip(
        'install', '--no-index', '-f', data.backends, project_dir
    )
    result.assert_installed('project', editable=False)


def test_pep517_install_with_reqs(script, tmpdir, data):
    """Backend generated requirements are installed in the build env"""
    project_dir = make_project(
        tmpdir, requires=['test_backend'],
        backend="test_backend"
    )
    project_dir.join("backend_reqs.txt").write("simplewheel")
    result = script.pip(
        'install', '--no-index',
        '-f', data.backends,
        '-f', data.packages,
        project_dir
    )
    result.assert_installed('project', editable=False)


def test_no_use_pep517_without_setup_py(script, tmpdir, data):
    """Using --no-use-pep517 requires setup.py"""
    project_dir = make_project(
        tmpdir, requires=['test_backend'],
        backend="test_backend"
    )
    result = script.pip(
        'install', '--no-index', '--no-use-pep517',
        '-f', data.backends,
        project_dir,
        expect_error=True
    )
    assert 'project does not have a setup.py' in result.stderr


def test_conflicting_pep517_backend_requirements(script, tmpdir, data):
    project_dir = make_project(
        tmpdir, requires=['test_backend', 'simplewheel==1.0'],
        backend="test_backend"
    )
    project_dir.join("backend_reqs.txt").write("simplewheel==2.0")
    result = script.pip(
        'install', '--no-index',
        '-f', data.backends,
        '-f', data.packages,
        project_dir,
        expect_error=True
    )
    assert (
        result.returncode != 0 and
        ('Some build dependencies for %s conflict with the backend '
         'dependencies: simplewheel==1.0 is incompatible with '
         'simplewheel==2.0.' % path_to_url(project_dir)) in result.stderr
    ), str(result)


def test_pep517_backend_requirements_already_satisfied(script, tmpdir, data):
    project_dir = make_project(
        tmpdir, requires=['test_backend', 'simplewheel==1.0'],
        backend="test_backend"
    )
    project_dir.join("backend_reqs.txt").write("simplewheel")
    result = script.pip(
        'install', '--no-index',
        '-f', data.backends,
        '-f', data.packages,
        project_dir,
    )
    assert 'Installing backend dependencies:' not in result.stdout


def test_pep517_install_with_no_cache_dir(script, tmpdir, data):
    """Check builds with a custom backends work, even with no cache.
    """
    project_dir = make_project(
        tmpdir, requires=['test_backend'],
        backend="test_backend"
    )
    result = script.pip(
        'install', '--no-cache-dir', '--no-index', '-f', data.backends,
        project_dir,
    )
    result.assert_installed('project', editable=False)


def make_pyproject_with_setup(tmpdir, build_system=True, set_backend=True):
    project_dir = (tmpdir / 'project').mkdir()
    setup_script = (
        'from setuptools import setup\n'
    )
    expect_script_dir_on_path = True
    if build_system:
        buildsys = {
            'requires': ['setuptools', 'wheel'],
        }
        if set_backend:
            buildsys['build-backend'] = 'setuptools.build_meta'
            expect_script_dir_on_path = False
        project_data = pytoml.dumps({'build-system': buildsys})
    else:
        project_data = ''

    if expect_script_dir_on_path:
        setup_script += (
            'from pep517_test import __version__\n'
        )
    else:
        setup_script += (
            'try:\n'
            '    import pep517_test\n'
            'except ImportError:\n'
            '    pass\n'
            'else:\n'
            '    raise RuntimeError("Source dir incorrectly on sys.path")\n'
        )

    setup_script += (
        'setup(name="pep517_test", version="0.1", packages=["pep517_test"])'
    )

    project_dir.join('pyproject.toml').write(project_data)
    project_dir.join('setup.py').write(setup_script)
    package_dir = (project_dir / "pep517_test").mkdir()
    package_dir.join('__init__.py').write('__version__ = "0.1"')
    return project_dir, "pep517_test"


def test_no_build_system_section(script, tmpdir, data, common_wheels):
    """Check builds with setup.py, pyproject.toml, but no build-system section.
    """
    project_dir, name = make_pyproject_with_setup(tmpdir, build_system=False)
    result = script.pip(
        'install', '--no-cache-dir', '--no-index', '-f', common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)


def test_no_build_backend_entry(script, tmpdir, data, common_wheels):
    """Check builds with setup.py, pyproject.toml, but no build-backend-entry.
    """
    project_dir, name = make_pyproject_with_setup(tmpdir, set_backend=False)
    result = script.pip(
        'install', '--no-cache-dir', '--no-index', '-f', common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)


def test_explicit_setuptools_backend(script, tmpdir, data, common_wheels):
    """Check builds with setup.py, pyproject.toml, and a build-system entry.
    """
    project_dir, name = make_pyproject_with_setup(tmpdir)
    result = script.pip(
        'install', '--no-cache-dir', '--no-index', '-f', common_wheels,
        project_dir,
    )
    result.assert_installed(name, editable=False)
