from typing import Dict, List, Optional, Union

import pytest

from pip._internal.utils.misc import merge_config_settings


@pytest.mark.parametrize(
    "reqs, cli, expected",
    [
        ({"foo": "bar"}, {"foo": ["baz"]}, {"foo": ["bar", "baz"]}),
        ({"foo": "bar"}, {"foo": "baz"}, {"foo": ["bar", "baz"]}),
        ({"foo": ["bar"]}, {"foo": ["baz"]}, {"foo": ["bar", "baz"]}),
        ({"foo": ["bar"]}, {"foo": "baz"}, {"foo": ["bar", "baz"]}),
        ({"foo": "bar"}, {"foo": ["baz"]}, {"foo": ["bar", "baz"]}),
        ({"foo": "bar"}, None, {"foo": "bar"}),
        (None, {"foo": ["bar"]}, {"foo": ["bar"]}),
    ],
)
def test_merge_config_settings(
    reqs: Optional[Dict[str, Union[str, List[str]]]],
    cli: Optional[Dict[str, Union[str, List[str]]]],
    expected: Dict[str, Union[str, List[str]]],
) -> None:
    assert merge_config_settings(reqs, cli) == expected
