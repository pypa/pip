import dataclasses
import hashlib
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from pip._vendor.typing_extensions import Self

T = TypeVar("T")


class FromDictProtocol(Protocol):
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self": ...


FromDictProtocolT = TypeVar("FromDictProtocolT", bound=FromDictProtocol)


class SingleArgConstructor(Protocol):
    def __init__(self, value: Any) -> None: ...


SingleArgConstructorT = TypeVar("SingleArgConstructorT", bound=SingleArgConstructor)

PYLOCK_FILE_NAME_RE = re.compile(r"^pylock\.([^.]+)\.toml$")


def is_valid_pylock_file_name(path: Path) -> bool:
    return path.name == "pylock.toml" or bool(PYLOCK_FILE_NAME_RE.match(path.name))


def _toml_key(key: str) -> str:
    return key.replace("_", "-")


def _toml_value(key: str, value: T) -> Union[str, List[str], T]:
    if isinstance(value, (Version, Marker, SpecifierSet)):
        return str(value)
    if isinstance(value, list) and key == "environments":
        return [str(v) for v in value]
    return value


def _toml_dict_factory(data: List[Tuple[str, Any]]) -> Dict[str, Any]:
    return {
        _toml_key(key): _toml_value(key, value)
        for key, value in data
        if value is not None and value != []
    }


def _get(d: Dict[str, Any], expected_type: Type[T], key: str) -> Optional[T]:
    """Get value from dictionary and verify expected type."""
    value = d.get(key)
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise PylockValidationError(
            f"{key!r} has unexpected type {type(value).__name__} "
            f"(expected {expected_type.__name__})"
        )
    return value


def _get_required(d: Dict[str, Any], expected_type: Type[T], key: str) -> T:
    """Get required value from dictionary and verify expected type."""
    value = _get(d, expected_type, key)
    if value is None:
        raise PylockRequiredKeyError(key)
    return value


def _get_list(
    d: Dict[str, Any], expected_item_type: Type[T], key: str
) -> Optional[List[T]]:
    """Get list value from dictionary and verify expected items type."""
    value = _get(d, list, key)
    if value is None:
        return None
    for i, item in enumerate(value):
        if not isinstance(item, expected_item_type):
            raise PylockValidationError(
                f"Item {i} of {key!r} has unexpected type {type(item).__name__} "
                f"(expected {expected_item_type.__name__})"
            )
    return value


def _get_as(
    d: Dict[str, Any],
    expected_type: Type[T],
    target_type: Type[SingleArgConstructorT],
    key: str,
) -> Optional[SingleArgConstructorT]:
    """Get value from dictionary, verify expected type, convert to target type.

    This assumes the target_type constructor accepts the value.
    """
    value = _get(d, expected_type, key)
    if value is None:
        return None
    try:
        return target_type(value)
    except Exception as e:
        raise PylockValidationError(f"Error in {key!r}: {e}") from e


def _get_required_as(
    d: Dict[str, Any],
    expected_type: Type[T],
    target_type: Type[SingleArgConstructorT],
    key: str,
) -> SingleArgConstructorT:
    """Get required value from dictionary, verify expected type,
    convert to target type."""
    value = _get_as(d, expected_type, target_type, key)
    if value is None:
        raise PylockRequiredKeyError(key)
    return value


def _get_list_as(
    d: Dict[str, Any],
    expected_item_type: Type[T],
    target_item_type: Type[SingleArgConstructorT],
    key: str,
) -> Optional[List[SingleArgConstructorT]]:
    """Get list value from dictionary and verify expected items type."""
    value = _get_list(d, expected_item_type, key)
    if value is None:
        return None
    result = []
    for i, item in enumerate(value):
        try:
            result.append(target_item_type(item))
        except Exception as e:
            raise PylockValidationError(f"Error in item {i} of {key!r}: {e}") from e
    return result


def _get_object(
    d: Dict[str, Any], target_type: Type[FromDictProtocolT], key: str
) -> Optional[FromDictProtocolT]:
    """Get dictionary value from dictionary and convert to dataclass."""
    value = _get(d, dict, key)
    if value is None:
        return None
    try:
        return target_type.from_dict(value)
    except Exception as e:
        raise PylockValidationError(f"Error in {key!r}: {e}") from e


def _get_list_of_objects(
    d: Dict[str, Any], target_item_type: Type[FromDictProtocolT], key: str
) -> Optional[List[FromDictProtocolT]]:
    """Get list value from dictionary and convert items to dataclass."""
    value = _get(d, list, key)
    if value is None:
        return None
    result = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise PylockValidationError(f"Item {i} of {key!r} is not a table")
        try:
            result.append(target_item_type.from_dict(item))
        except Exception as e:
            raise PylockValidationError(f"Error in item {i} of {key!r}: {e}") from e
    return result


def _get_required_list_of_objects(
    d: Dict[str, Any], target_type: Type[FromDictProtocolT], key: str
) -> List[FromDictProtocolT]:
    """Get required list value from dictionary and convert items to dataclass."""
    result = _get_list_of_objects(d, target_type, key)
    if result is None:
        raise PylockRequiredKeyError(key)
    return result


def _exactly_one(iterable: Iterable[object]) -> bool:
    found = False
    for item in iterable:
        if item:
            if found:
                return False
            found = True
    return found


def _validate_hashes(hashes: Dict[str, Any]) -> None:
    if not hashes:
        raise PylockValidationError("At least one hash must be provided")
    if not any(algo in hashlib.algorithms_guaranteed for algo in hashes):
        raise PylockValidationError(
            "At least one hash algorithm must be in hashlib.algorithms_guaranteed"
        )
    if not all(isinstance(hash, str) for hash in hashes.values()):
        raise PylockValidationError("Hash values must be strings")


class PylockValidationError(Exception):
    pass


class PylockRequiredKeyError(PylockValidationError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Missing required key {key!r}")


class PylockUnsupportedVersionError(PylockValidationError):
    pass


@dataclass
class PackageVcs:
    type: str
    url: Optional[str]
    path: Optional[str]
    requested_revision: Optional[str]
    commit_id: str
    subdirectory: Optional[str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for vcs package")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            type=_get_required(d, str, "type"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            requested_revision=_get(d, str, "requested-revision"),
            commit_id=_get_required(d, str, "commit-id"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass
class PackageDirectory:
    path: str
    editable: Optional[bool]
    subdirectory: Optional[str]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            path=_get_required(d, str, "path"),
            editable=_get(d, bool, "editable"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass
class PackageArchive:
    url: Optional[str]
    path: Optional[str]
    size: Optional[int]
    upload_time: Optional[datetime]
    hashes: Dict[str, str]
    subdirectory: Optional[str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for archive package")
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            upload_time=_get(d, datetime, "upload-time"),
            hashes=_get_required(d, dict, "hashes"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass
class PackageSdist:
    name: str
    upload_time: Optional[datetime]
    url: Optional[str]
    path: Optional[str]
    size: Optional[int]
    hashes: Dict[str, str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for sdist package")
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            name=_get_required(d, str, "name"),
            upload_time=_get(d, datetime, "upload-time"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, dict, "hashes"),
        )


@dataclass
class PackageWheel:
    name: str
    upload_time: Optional[datetime]
    url: Optional[str]
    path: Optional[str]
    size: Optional[int]
    hashes: Dict[str, str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for wheel package")
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        wheel = cls(
            name=_get_required(d, str, "name"),
            upload_time=_get(d, datetime, "upload-time"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, dict, "hashes"),
        )
        return wheel


@dataclass
class Package:
    name: str
    version: Optional[Version]
    marker: Optional[Marker]
    requires_python: Optional[SpecifierSet]
    dependencies: Optional[List[Dict[str, Any]]]
    vcs: Optional[PackageVcs]
    directory: Optional[PackageDirectory]
    archive: Optional[PackageArchive]
    index: Optional[str]
    sdist: Optional[PackageSdist]
    wheels: Optional[List[PackageWheel]]
    attestation_identities: Optional[List[Dict[str, Any]]]
    tool: Optional[Dict[str, Any]]

    def __post_init__(self) -> None:
        if self.sdist or self.wheels:
            if any([self.vcs, self.directory, self.archive]):
                raise PylockValidationError(
                    "None of vcs, directory, archive "
                    "must be set if sdist or wheels are set"
                )
        else:
            # no sdist nor wheels
            if not _exactly_one([self.vcs, self.directory, self.archive]):
                raise PylockValidationError(
                    "Exactly one of vcs, directory, archive must be set "
                    "if sdist and wheels are not set"
                )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        package = cls(
            name=_get_required(d, str, "name"),
            version=_get_as(d, str, Version, "version"),
            requires_python=_get_as(d, str, SpecifierSet, "requires-python"),
            dependencies=_get_list(d, dict, "dependencies"),
            marker=_get_as(d, str, Marker, "marker"),
            vcs=_get_object(d, PackageVcs, "vcs"),
            directory=_get_object(d, PackageDirectory, "directory"),
            archive=_get_object(d, PackageArchive, "archive"),
            index=_get(d, str, "index"),
            sdist=_get_object(d, PackageSdist, "sdist"),
            wheels=_get_list_of_objects(d, PackageWheel, "wheels"),
            attestation_identities=_get_list(d, dict, "attestation-identities"),
            tool=_get(d, dict, "tool"),
        )
        return package


@dataclass
class Pylock:
    lock_version: Version
    environments: Optional[List[Marker]]
    requires_python: Optional[SpecifierSet]
    extras: List[str]
    dependency_groups: List[str]
    default_groups: List[str]
    created_by: str
    packages: List[Package]
    tool: Optional[Dict[str, Any]]

    def __post_init__(self) -> None:
        if self.lock_version < Version("1") or self.lock_version >= Version("2"):
            raise PylockUnsupportedVersionError(
                f"pylock version {self.lock_version} is not supported"
            )
        if self.lock_version > Version("1.0"):
            logging.warning(
                "pylock minor version %s is not supported", self.lock_version
            )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=_toml_dict_factory)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            lock_version=_get_required_as(d, str, Version, "lock-version"),
            environments=_get_list_as(d, str, Marker, "environments"),
            extras=_get_list(d, str, "extras") or [],
            dependency_groups=_get_list(d, str, "dependency-groups") or [],
            default_groups=_get_list(d, str, "default-groups") or [],
            created_by=_get_required(d, str, "created-by"),
            requires_python=_get_as(d, str, SpecifierSet, "requires-python"),
            packages=_get_required_list_of_objects(d, Package, "packages"),
            tool=_get(d, dict, "tool"),
        )
