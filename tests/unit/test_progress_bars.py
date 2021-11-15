from typing import Dict

import pytest

from pip._internal.cli.progress_bars import DefaultDownloadProgressBar


@pytest.mark.parametrize(
    "value, downloaded, download_speed, pretty_eta",
    [
        (
            {"avg": 5, "index": 10, "max": 100},
            "10 bytes",
            "0 bytes/s",
            "eta 0:07:30",
        ),
        (
            {"avg": 5, "index": 100, "max": 100},
            "100 bytes",
            "",
            "",
        ),
    ],
)
def test_display_infos(
    value: Dict[str, int], downloaded: str, download_speed: str, pretty_eta: str
) -> None:
    bar = DefaultDownloadProgressBar(**value)

    assert bar.downloaded == downloaded, f"actual: {bar.downloaded}"
    assert bar.download_speed == download_speed, f"actual: {bar.download_speed}"
    assert bar.pretty_eta == pretty_eta, f"actual: {bar.pretty_eta}"
