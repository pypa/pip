import logging
import os
from pathlib import Path
from typing import cast
from unittest import mock

import pytest
from pip._vendor.packaging.utils import NormalizedName

from pip._internal.metadata import (
    BaseDistribution,
    get_directory_distribution,
    get_environment,
    get_wheel_distribution,
)
from pip._internal.metadata.base import FilesystemWheel
from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, ArchiveInfo
from tests.lib.wheel import make_wheel


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


def test_metadata_reads_egg_info_requires_txt(tmp_path: Path) -> None:
    """Check Requires-Dist is obtained from requires.txt if absent in PKG-INFO."""
    egg_info_path = tmp_path / "whatever.egg-info"
    egg_info_path.mkdir()
    dist = get_directory_distribution(str(egg_info_path))
    assert dist.installed_with_setuptools_egg_info
    pkg_info_path = egg_info_path / "PKG-INFO"
    pkg_info_path.write_text("Name: whatever\n")
    egg_info_path.joinpath("requires.txt").write_text("pkga\npkgb\n")
    assert dist.metadata.get_all("Requires-Dist") == ["pkga", "pkgb"]


def test_metadata_pkg_info_requires_priority(tmp_path: Path) -> None:
    """Check Requires-Dist in PKG-INFO has priority over requires.txt."""
    egg_info_path = tmp_path / "whatever.egg-info"
    egg_info_path.mkdir()
    dist = get_directory_distribution(str(egg_info_path))
    assert dist.installed_with_setuptools_egg_info
    pkg_info_path = egg_info_path / "PKG-INFO"
    pkg_info_path.write_text(
        "Name: whatever\nRequires-Dist: pkgc\nRequires-Dist: pkgd\n"
    )
    egg_info_path.joinpath("requires.txt").write_text("pkga\npkgb\n")
    assert dist.metadata.get_all("Requires-Dist") == ["pkgc", "pkgd"]


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


def test_metadata_dict(tmp_path: Path) -> None:
    """Basic test of BaseDistribution metadata_dict.

    More tests are available in the original pkg_metadata project where this
    function comes from, and which we may vendor in the future.
    """
    wheel_path = make_wheel(name="pkga", version="1.0.1").save_to_dir(tmp_path)
    wheel = FilesystemWheel(wheel_path)
    dist = get_wheel_distribution(wheel, "pkga")
    metadata_dict = dist.metadata_dict
    assert metadata_dict["name"] == "pkga"
    assert metadata_dict["version"] == "1.0.1"


def test_no_dist_found_in_wheel(tmp_path: Path) -> None:
    location = os.fspath(tmp_path.joinpath("pkg-1-py3-none-any.whl"))
    make_wheel(name="pkg", version="1").save_to(location)
    assert get_environment([location]).get_distribution("pkg") is None


def test_dist_found_in_directory_named_whl(tmp_path: Path) -> None:
    dir_path = tmp_path.joinpath("pkg-1-py3-none-any.whl")
    info_path = dir_path.joinpath("pkg-1.dist-info")
    info_path.mkdir(parents=True)
    info_path.joinpath("METADATA").write_text("Name: pkg")
    location = os.fspath(dir_path)
    dist = get_environment([location]).get_distribution("pkg")
    assert dist is not None and dist.location is not None
    assert Path(dist.location) == Path(location)


def test_dist_found_in_zip(tmp_path: Path) -> None:
    location = os.fspath(tmp_path.joinpath("pkg.zip"))
    make_wheel(name="pkg", version="1").save_to(location)
    dist = get_environment([location]).get_distribution("pkg")
    assert dist is not None and dist.location is not None
    assert Path(dist.location) == Path(location)


@pytest.mark.parametrize(
    "path",
    (
        "/path/to/foo.egg-info".replace("/", os.path.sep),
        # Tests issue fixed by https://github.com/pypa/pip/pull/2530
        "/path/to/foo.egg-info/".replace("/", os.path.sep),
    ),
)
def test_trailing_slash_directory_metadata(path: str) -> None:
    dist = get_directory_distribution(path)
    assert dist.raw_name == dist.canonical_name == "foo"
    assert dist.location == "/path/to".replace("/", os.path.sep)
