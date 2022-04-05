import logging
from typing import cast
from unittest import mock

import pytest
from pip._vendor.packaging.utils import NormalizedName

from pip._internal.metadata import BaseDistribution
from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, ArchiveInfo


@mock.patch.object(BaseDistribution, "read_text", side_effect=FileNotFoundError)
def test_dist_get_direct_url_no_metadata(mock_read_text: mock.Mock) -> None:
    class FakeDistribution(BaseDistribution):
        pass

    dist = FakeDistribution()
    assert dist.direct_url is None
    mock_read_text.assert_called_once_with(DIRECT_URL_METADATA_NAME)


@mock.patch.object(BaseDistribution, "read_text", return_value="{}")
def test_dist_get_direct_url_invalid_json(
    mock_read_text: mock.Mock, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeDistribution(BaseDistribution):
        canonical_name = cast(NormalizedName, "whatever")  # Needed for error logging.

    dist = FakeDistribution()
    with caplog.at_level(logging.WARNING):
        assert dist.direct_url is None

    mock_read_text.assert_called_once_with(DIRECT_URL_METADATA_NAME)
    assert (
        caplog.records[-1]
        .getMessage()
        .startswith(
            "Error parsing direct_url.json for whatever:",
        )
    )


@mock.patch.object(
    BaseDistribution,
    "read_text",
    return_value='{"url": "https://e.c/p.tgz", "archive_info": {}}',
)
def test_dist_get_direct_url_valid_metadata(mock_read_text: mock.Mock) -> None:
    class FakeDistribution(BaseDistribution):
        pass

    dist = FakeDistribution()
    direct_url = dist.direct_url
    assert direct_url is not None
    mock_read_text.assert_called_once_with(DIRECT_URL_METADATA_NAME)
    assert direct_url.url == "https://e.c/p.tgz"
    assert isinstance(direct_url.info, ArchiveInfo)
