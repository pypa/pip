import os
from contextlib import ExitStack
from email import message_from_string
from io import BytesIO
from zipfile import ZipFile

import pytest

from pip._internal.exceptions import UnsupportedWheel
from pip._internal.utils import wheel
from tests.lib.path import Path


@pytest.fixture
def zip_dir():
    def make_zip(path: Path) -> ZipFile:
        buf = BytesIO()
        with ZipFile(buf, "w", allowZip64=True) as z:
            for dirpath, _, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(path, dirpath, filename)
                    # Zip files must always have / as path separator
                    archive_path = os.path.relpath(file_path, path).replace(
                        os.pathsep, "/"
                    )
                    z.write(file_path, archive_path)

        return stack.enter_context(ZipFile(buf, "r", allowZip64=True))

    stack = ExitStack()
    with stack:
        yield make_zip


def test_wheel_dist_info_dir_found(tmpdir, zip_dir):
    expected = "simple-0.1.dist-info"
    dist_info_dir = tmpdir / expected
    dist_info_dir.mkdir()
    dist_info_dir.joinpath("WHEEL").touch()
    assert wheel.wheel_dist_info_dir(zip_dir(tmpdir), "simple") == expected


def test_wheel_dist_info_dir_multiple(tmpdir, zip_dir):
    dist_info_dir_1 = tmpdir / "simple-0.1.dist-info"
    dist_info_dir_1.mkdir()
    dist_info_dir_1.joinpath("WHEEL").touch()
    dist_info_dir_2 = tmpdir / "unrelated-0.1.dist-info"
    dist_info_dir_2.mkdir()
    dist_info_dir_2.joinpath("WHEEL").touch()
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_dist_info_dir(zip_dir(tmpdir), "simple")
    assert "multiple .dist-info directories found" in str(e.value)


def test_wheel_dist_info_dir_none(tmpdir, zip_dir):
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_dist_info_dir(zip_dir(tmpdir), "simple")
    assert "directory not found" in str(e.value)


def test_wheel_dist_info_dir_wrong_name(tmpdir, zip_dir):
    dist_info_dir = tmpdir / "unrelated-0.1.dist-info"
    dist_info_dir.mkdir()
    dist_info_dir.joinpath("WHEEL").touch()
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_dist_info_dir(zip_dir(tmpdir), "simple")
    assert "does not start with 'simple'" in str(e.value)


def test_wheel_version_ok(tmpdir, data):
    assert wheel.wheel_version(message_from_string("Wheel-Version: 1.9")) == (1, 9)


def test_wheel_metadata_fails_missing_wheel(tmpdir, zip_dir):
    dist_info_dir = tmpdir / "simple-0.1.0.dist-info"
    dist_info_dir.mkdir()
    dist_info_dir.joinpath("METADATA").touch()

    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_metadata(zip_dir(tmpdir), dist_info_dir.name)
    assert "could not read" in str(e.value)


def test_wheel_metadata_fails_on_bad_encoding(tmpdir, zip_dir):
    dist_info_dir = tmpdir / "simple-0.1.0.dist-info"
    dist_info_dir.mkdir()
    dist_info_dir.joinpath("METADATA").touch()
    dist_info_dir.joinpath("WHEEL").write_bytes(b"\xff")

    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_metadata(zip_dir(tmpdir), dist_info_dir.name)
    assert "error decoding" in str(e.value)


def test_wheel_version_fails_on_no_wheel_version():
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_version(message_from_string(""))
    assert "missing Wheel-Version" in str(e.value)


@pytest.mark.parametrize(
    "version",
    [
        ("",),
        ("1.b",),
        ("1.",),
    ],
)
def test_wheel_version_fails_on_bad_wheel_version(version):
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_version(message_from_string(f"Wheel-Version: {version}"))
    assert "invalid Wheel-Version" in str(e.value)


def test_check_compatibility():
    name = "test"
    vc = wheel.VERSION_COMPATIBLE

    # Major version is higher - should be incompatible
    higher_v = (vc[0] + 1, vc[1])

    # test raises with correct error
    with pytest.raises(UnsupportedWheel) as e:
        wheel.check_compatibility(higher_v, name)
    assert "is not compatible" in str(e)

    # Should only log.warning - minor version is greater
    higher_v = (vc[0], vc[1] + 1)
    wheel.check_compatibility(higher_v, name)

    # These should work fine
    wheel.check_compatibility(wheel.VERSION_COMPATIBLE, name)

    # E.g if wheel to install is 1.0 and we support up to 1.2
    lower_v = (vc[0], max(0, vc[1] - 1))
    wheel.check_compatibility(lower_v, name)
