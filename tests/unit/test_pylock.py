from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

from pip._internal.models.pylock import (
    Package,
    PackageDirectory,
    PackageWheel,
    Pylock,
    PylockRequiredKeyError,
    PylockUnsupportedVersionError,
    PylockValidationError,
    _exactly_one,
    is_valid_pylock_path,
)


@pytest.mark.parametrize(
    "file_name,valid",
    [
        ("pylock.toml", True),
        ("pylock.spam.toml", True),
        ("pylock.json", False),
        ("pylock..toml", False),
    ],
)
def test_pylock_file_name(file_name: str, valid: bool) -> None:
    assert is_valid_pylock_path(Path(file_name)) is valid


def test_exactly_one() -> None:
    assert not _exactly_one([])
    assert not _exactly_one([False])
    assert not _exactly_one([False, False])
    assert not _exactly_one([True, True])
    assert _exactly_one([True])
    assert _exactly_one([True, False])


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
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == "Error in 'lock-version': Invalid version: '2.x'"


def test_pylock_missing_version() -> None:
    data = {
        "created-by": "pip",
        "packages": [],
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == "Missing required key 'lock-version'"


def test_pylock_missing_created_by() -> None:
    data = {
        "lock-version": "1.0",
        "packages": [],
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == "Missing required key 'created-by'"


def test_pylock_missing_packages() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "uv",
    }
    with pytest.raises(PylockRequiredKeyError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == "Missing required key 'packages'"


def test_pylock_packages_without_dist() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "packages": [{"name": "example", "version": "1.0"}],
    }
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == (
        "Error in item 0 of 'packages': "
        "Exactly one of vcs, directory, archive must be set "
        "if sdist and wheels are not set"
    )


def test_pylock_basic_package() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "requires-python": ">=3.10",
        "environments": ['os_name == "posix"'],
        "packages": [
            {
                "name": "example",
                "version": "1.0",
                "marker": 'os_name == "posix"',
                "requires-python": "!=3.10.1,>=3.10",
                "directory": {
                    "path": ".",
                    "editable": False,
                },
            }
        ],
    }
    pylock = Pylock.from_dict(data)
    assert pylock.environments == [Marker('os_name == "posix"')]
    package = pylock.packages[0]
    assert package.version == Version("1.0")
    assert package.marker == Marker('os_name == "posix"')
    assert package.requires_python == SpecifierSet(">=3.10, !=3.10.1")
    assert pylock.to_dict() == data


def test_pylock_invalid_archive() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "requires-python": ">=3.10",
        "environments": ['os_name == "posix"'],
        "packages": [
            {
                "name": "example",
                "archive": {
                    # "path": "example.tar.gz",
                    "hashes": {"sha256": "f" * 40},
                },
            }
        ],
    }
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == (
        "Error in item 0 of 'packages': "
        "Error in 'archive': "
        "path or url must be provided"
    )


def test_pylock_invalid_wheel() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "requires-python": ">=3.10",
        "environments": ['os_name == "posix"'],
        "packages": [
            {
                "name": "example",
                "wheels": [
                    {
                        "name": "example-1.0-py3-none-any.whl",
                        "path": "./example-1.0-py3-none-any.whl",
                        # "hashes": {"sha256": "f" * 40},
                    }
                ],
            }
        ],
    }
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == (
        "Error in item 0 of 'packages': "
        "Error in item 0 of 'wheels': "
        "Missing required key 'hashes'"
    )


def test_pylock_invalid_environments() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "environments": [
            'os_name == "posix"',
            'invalid_marker == "..."',
        ],
        "packages": [],
    }
    with pytest.raises(PylockValidationError) as exc_info:
        Pylock.from_dict(data)
    assert str(exc_info.value) == (
        "Error in item 1 of 'environments': "
        "Expected a marker variable or quoted string\n"
        '    invalid_marker == "..."\n'
        "    ^"
    )


def test_pylock_extras_and_groups() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "extras": ["feat1", "feat2"],
        "dependency-groups": ["dev", "docs"],
        "default-groups": ["dev"],
        "packages": [],
    }
    pylock = Pylock.from_dict(data)
    assert pylock.extras == ["feat1", "feat2"]
    assert pylock.dependency_groups == ["dev", "docs"]
    assert pylock.default_groups == ["dev"]


def test_pylock_tool() -> None:
    data = {
        "lock-version": "1.0",
        "created-by": "pip",
        "packages": [
            {
                "name": "example",
                "sdist": {
                    "name": "example-1.0.tar.gz",
                    "path": "./example-1.0.tar.gz",
                    "upload-time": datetime(2023, 10, 1, 0, 0),
                    "hashes": {"sha256": "f" * 40},
                },
                "tool": {"pip": {"foo": "bar"}},
            }
        ],
        "tool": {"pip": {"version": "25.2"}},
    }
    pylock = Pylock.from_dict(data)
    assert pylock.tool == {"pip": {"version": "25.2"}}
    package = pylock.packages[0]
    assert package.tool == {"pip": {"foo": "bar"}}


@pytest.mark.parametrize(
    "hashes,expected_error",
    [
        (
            {
                "sha2": "f" * 40,
            },
            "At least one hash algorithm must be in hashlib.algorithms_guaranteed",
        ),
        (
            {
                "sha256": "f" * 40,
                "md5": 1,
            },
            "Hash values must be strings",
        ),
        (
            {},
            "At least one hash must be provided",
        ),
    ],
)
def test_hash_validation(hashes: Dict[str, Any], expected_error: str) -> None:
    with pytest.raises(PylockValidationError) as exc_info:
        PackageWheel(
            name="example-1.0-py3-none-any.whl",
            upload_time=None,
            url="https://example.com/example-1.0-py3-none-any.whl",
            path=None,
            size=None,
            hashes=hashes,
        )
    assert str(exc_info.value) == expected_error


def test_is_direct() -> None:
    direct_package = Package(
        name="example",
        directory=PackageDirectory(path="."),
    )
    assert direct_package.is_direct
    wheel_package = Package(
        name="example",
        wheels=[
            PackageWheel(
                url="https://example.com/example-1.0-py3-none-any.whl",
                hashes={"sha256": "f" * 40},
            )
        ],
    )
    assert not wheel_package.is_direct
