from pip._vendor import pytoml

from pip._internal.build_env import BuildEnvironment
from pip._internal.download import PipSession
from pip._internal.index import PackageFinder
from pip._internal.req import InstallRequirement


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
