import pytest
import logging

from pip._internal.models.link import Link
from pip._internal.network.download import _prepare_download
from tests.lib.requests_mocks import MockResponse


@pytest.mark.parametrize("url, headers, from_cache, expected", [
    ('http://example.com/foo.tgz', {}, False,
        "Downloading http://example.com/foo.tgz"),
    ('http://example.com/foo.tgz', {'content-length': 2}, False,
        "Downloading http://example.com/foo.tgz (2 bytes)"),
    ('http://example.com/foo.tgz', {'content-length': 2}, True,
        "Using cached http://example.com/foo.tgz (2 bytes)"),
    ('https://files.pythonhosted.org/foo.tgz', {}, False,
        "Downloading foo.tgz"),
    ('https://files.pythonhosted.org/foo.tgz', {'content-length': 2}, False,
        "Downloading foo.tgz (2 bytes)"),
    ('https://files.pythonhosted.org/foo.tgz', {'content-length': 2}, True,
        "Using cached foo.tgz"),
])
def test_prepare_download__log(caplog, url, headers, from_cache, expected):
    caplog.set_level(logging.INFO)
    resp = MockResponse(b'')
    resp.url = url
    resp.headers = headers
    if from_cache:
        resp.from_cache = from_cache
    link = Link(url)
    _prepare_download(resp, link, progress_bar="on")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'INFO'
    assert expected in record.message
