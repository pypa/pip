from typing import Dict, List, Union

from pip._internal.utils.misc import merge_config_settings


def test_merge_config_settings() -> None:
    reqs: Dict[str, Union[str, List[str]]] = {
        "foo": "bar",
        "bar": "foo",
        "foobar": ["bar"],
        "baz": ["foo"],
    }
    cli: Dict[str, Union[str, List[str]]] = {
        "foo": ["baz"],
        "bar": "bar",
        "foobar": ["baz"],
        "baz": "bar",
    }
    expected = {
        "foo": ["bar", "baz"],
        "bar": ["foo", "bar"],
        "foobar": ["bar", "baz"],
        "baz": ["foo", "bar"],
    }
    assert merge_config_settings(reqs, cli) == expected
