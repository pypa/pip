import json

from tests.lib import create_basic_wheel_for_package


def assert_installed(script, **kwargs):
    ret = script.pip('list', '--format=json')
    installed = set(
        (val['name'], val['version'])
        for val in json.loads(ret.stdout)
    )
    assert all(item in installed for item in kwargs.items()), \
        "{!r} not all in {!r}".format(kwargs, installed)


def assert_not_installed(script, *args):
    ret = script.pip("list", "--format=json")
    installed = set(val["name"] for val in json.loads(ret.stdout))
    assert all(a not in installed for a in args), \
        "{!r} contained in {!r}".format(args, installed)


def test_new_resolver_can_install(script):
    create_basic_wheel_for_package(
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
    create_basic_wheel_for_package(
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
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    create_basic_wheel_for_package(
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
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
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


def test_new_resolver_ignore_dependencies(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index", "--no-deps",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0")
    assert_not_installed(script, "dep")


def test_new_resolver_installs_extras(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        extras={"add": ["dep"]},
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base[add,missing]",
        expect_stderr=True,
    )
    assert "WARNING: Invalid extras specified" in result.stderr, str(result)
    assert ": missing" in result.stderr, str(result)
    assert_installed(script, base="0.1.0", dep="0.1.0")
