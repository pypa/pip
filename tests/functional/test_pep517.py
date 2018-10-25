from pip._vendor import pytoml

from pip._internal.build_env import BuildEnvironment
from pip._internal.download import PipSession
from pip._internal.index import PackageFinder
from pip._internal.req import InstallRequirement


def make_project(tmpdir, requires=[], backend=None):
    buildsys = {'requires': requires}
    if backend:
        buildsys['build-backend'] = backend
    data = pytoml.dumps({'build-system': buildsys})
    tmpdir.join('pyproject.toml').write(data)
    return tmpdir


def test_backend(tmpdir, data):
    """Can we call a requirement's backend successfully?"""
    project = make_project(tmpdir, backend="dummy_backend")
    req = InstallRequirement(None, None, source_dir=project)
    req.load_pyproject_toml()
    env = BuildEnvironment()
    finder = PackageFinder([data.backends], [], session=PipSession())
    env.install_requirements(finder, ["dummy_backend"], 'normal', "Installing")
    conflicting, missing = env.check_requirements(["dummy_backend"])
    assert not conflicting and not missing
    assert hasattr(req.pep517_backend, 'build_wheel')
    with env:
        assert req.pep517_backend.build_wheel("dir") == "Backend called"
