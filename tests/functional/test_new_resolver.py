import json
from tests.lib import create_basic_wheel_for_package


def assert_installed(script, **kwargs):
    ret = script.pip('list', '--format=json')
    installed = set(
        (val['name'], val['version'])
        for val in json.loads(ret.stdout)
    )
    assert set(kwargs.items()) <= installed
        

def test_new_resolver_can_install(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert_installed(script, simple="0.1.0")


def test_new_resolver_can_install_with_version(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple==0.1.0"
    )
    assert_installed(script, simple="0.1.0")


def test_new_resolver_picks_latest_version(script):
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    package = create_basic_wheel_for_package(
        script,
        "simple",
        "0.2.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert_installed(script, simple="0.2.0")

def test_new_resolver_installs_dependencies(script):
    package = create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    package = create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0", dep="0.1.0")
