import pytest

from pip._internal.utils.distutils_args import parse_distutils_args


def test_unknown_option_is_ok():
    result = parse_distutils_args(["--foo"])
    assert not result


def test_option_is_returned():
    result = parse_distutils_args(["--prefix=hello"])
    assert result["prefix"] == "hello"


def test_options_are_clobbered():
    # Matches the current setuptools behavior that the last argument
    # wins.
    result = parse_distutils_args(["--prefix=hello", "--prefix=world"])
    assert result["prefix"] == "world"


def test_multiple_options_work():
    result = parse_distutils_args(["--prefix=hello", "--root=world"])
    assert result["prefix"] == "hello"
    assert result["root"] == "world"


def test_multiple_invocations_do_not_keep_options():
    result = parse_distutils_args(["--prefix=hello1"])
    assert len(result) == 1
    assert result["prefix"] == "hello1"

    result = parse_distutils_args(["--root=world1"])
    assert len(result) == 1
    assert result["root"] == "world1"


@pytest.mark.parametrize(
    "name,value",
    [
        ("exec-prefix", "1"),
        ("home", "2"),
        ("install-base", "3"),
        ("install-data", "4"),
        ("install-headers", "5"),
        ("install-lib", "6"),
        ("install-platlib", "7"),
        ("install-purelib", "8"),
        ("install-scripts", "9"),
        ("prefix", "10"),
        ("root", "11"),
    ],
)
def test_all_value_options_work(name, value):
    result = parse_distutils_args([f"--{name}={value}"])
    key_name = name.replace("-", "_")
    assert result[key_name] == value


def test_user_option_works():
    result = parse_distutils_args(["--user"])
    assert result["user"] == 1
