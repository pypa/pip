import pytest

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.version import Version

from pip._internal.models.pylock import (
    Pylock,
    PylockRequiredKeyError,
    PylockUnsupportedVersionError,
    PylockValidationError,
)


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_pylock_version(version: str) -> None:
    data = {
        "lock-version": version,
        "created-by": "pip",
        "packages": [],
    }
    Pylock.from_dict(data)


def test_pylock_unsupported_version() -> None:
    data = {
        "lock-version": "2.0",
        "created-by": "pip",
        "packages": [],
    }
    with pytest.raises(PylockUnsupportedVersionError):
        Pylock.from_dict(data)


def test_pylock_invalid_version() -> None:
    data = {
        "lock-version": "2.x",
        "created-by": "pip",
        "packages": [],
    }
    with pytest.raises(PylockUnsupportedVersionError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == "Error in 'lock-version': Invalid version: '2.x'"


def test_pylock_missing_version() -> None:
    data = {
        "created-by": "pip",
        "packages": [],
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert exc_info.value.key == "lock-version"


def test_pylock_missing_created_by() -> None:
    data = {
        "lock-version": "1.0",
        "packages": [],
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert exc_info.value.key == "created-by"


def test_pylock_missing_packages() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "uv",
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert exc_info.value.key == "packages"


def test_pylock_packages_without_dist() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "packages": [{"name": "example", "version": "1.0"}],
    }
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert (
        str(exc_info.value)
        == "Exactly one of vcs, directory, archive, sdist, wheels must be set"
    )


def test_pylock_basic_package() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "packages": [
            {
                "name": "example",
                "version": "1.0",
                "marker": 'os_name == "posix"',
                "directory": {
                    "path": ".",
                    "editable": False,
                },
            }
        ],
    }
    pylock = Pylock.from_dict(data)
    package = pylock.packages[0]
    assert package.version == Version("1.0")
    assert package.marker == Marker('os_name == "posix"')
    assert pylock.to_dict() == data
