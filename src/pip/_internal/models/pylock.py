import dataclasses
import hashlib
import logging
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
)

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from pip._vendor.typing_extensions import Self

__all__ = [
    "Package",
    "PackageVcs",
    "PackageDirectory",
    "PackageArchive",
    "PackageSdist",
    "PackageWheel",
    "Pylock",
    "PylockValidationError",
    "PylockUnsupportedVersionError",
    "is_valid_pylock_path",
]

T = TypeVar("T")


class FromDictProtocol(Protocol):
    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self": ...


FromDictProtocolT = TypeVar("FromDictProtocolT", bound=FromDictProtocol)


class SingleArgConstructor(Protocol):
    def __init__(self, value: Any) -> None: ...


SingleArgConstructorT = TypeVar("SingleArgConstructorT", bound=SingleArgConstructor)

PYLOCK_FILE_NAME_RE = re.compile(r"^pylock\.([^.]+)\.toml$")


def is_valid_pylock_path(path: Path) -> bool:
    return path.name == "pylock.toml" or bool(PYLOCK_FILE_NAME_RE.match(path.name))


def _toml_key(key: str) -> str:
    return key.replace("_", "-")


def _toml_value(key: str, value: Any) -> Any:
    if isinstance(value, (Version, Marker, SpecifierSet)):
        return str(value)
    if isinstance(value, Sequence) and key == "environments":
        return [str(v) for v in value]
    return value


def _toml_dict_factory(data: List[Tuple[str, Any]]) -> Dict[str, Any]:
    return {
        _toml_key(key): _toml_value(key, value)
        for key, value in data
        if value is not None and value != []
    }


def _get(d: Mapping[str, Any], expected_type: Type[T], key: str) -> Optional[T]:
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


def _get_required(d: Mapping[str, Any], expected_type: Type[T], key: str) -> T:
    """Get required value from dictionary and verify expected type."""
    value = _get(d, expected_type, key)
    if value is None:
        raise PylockRequiredKeyError(key)
    return value


def _get_list(
    d: Mapping[str, Any], expected_item_type: Type[T], key: str
) -> Optional[Sequence[T]]:
    """Get list value from dictionary and verify expected items type."""
    value = _get(d, Sequence, key)  # type: ignore[type-abstract]
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
    d: Mapping[str, Any],
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
    d: Mapping[str, Any],
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
    d: Mapping[str, Any],
    expected_item_type: Type[T],
    target_item_type: Type[SingleArgConstructorT],
    key: str,
) -> Optional[Sequence[SingleArgConstructorT]]:
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
    d: Mapping[str, Any], target_type: Type[FromDictProtocolT], key: str
) -> Optional[FromDictProtocolT]:
    """Get dictionary value from dictionary and convert to dataclass."""
    value = _get(d, Mapping, key)  # type: ignore[type-abstract]
    if value is None:
        return None
    try:
        return target_type.from_dict(value)
    except Exception as e:
        raise PylockValidationError(f"Error in {key!r}: {e}") from e


def _get_list_of_objects(
    d: Mapping[str, Any], target_item_type: Type[FromDictProtocolT], key: str
) -> Optional[Sequence[FromDictProtocolT]]:
    """Get list value from dictionary and convert items to dataclass."""
    value = _get(d, Sequence, key)  # type: ignore[type-abstract]
    if value is None:
        return None
    result = []
    for i, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise PylockValidationError(f"Item {i} of {key!r} is not a table")
        try:
            result.append(target_item_type.from_dict(item))
        except Exception as e:
            raise PylockValidationError(f"Error in item {i} of {key!r}: {e}") from e
    return result


def _get_required_list_of_objects(
    d: Mapping[str, Any], target_type: Type[FromDictProtocolT], key: str
) -> Sequence[FromDictProtocolT]:
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


def _validate_path_url(path: Optional[str], url: Optional[str]) -> None:
    if not path and not url:
        raise PylockValidationError("path or url must be provided")


def _validate_hashes(hashes: Mapping[str, Any]) -> None:
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


@dataclass(frozen=True)
class PackageVcs:
    type: str
    url: Optional[str]  # = None
    path: Optional[str]  # = None
    requested_revision: Optional[str]  # = None
    commit_id: str
    subdirectory: Optional[str] = None

    def __init__(
        self,
        *,
        type: str,
        commit_id: str,
        url: Optional[str] = None,
        path: Optional[str] = None,
        requested_revision: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "type", type)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "requested_revision", requested_revision)
        object.__setattr__(self, "commit_id", commit_id)
        object.__setattr__(self, "subdirectory", subdirectory)
        # __post_init__ in Python 3.10+
        _validate_path_url(self.path, self.url)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        return cls(
            type=_get_required(d, str, "type"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            requested_revision=_get(d, str, "requested-revision"),
            commit_id=_get_required(d, str, "commit-id"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass(frozen=True)
class PackageDirectory:
    path: str
    editable: Optional[bool] = None
    subdirectory: Optional[str] = None

    def __init__(
        self,
        *,
        path: str,
        editable: Optional[bool] = None,
        subdirectory: Optional[str] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "editable", editable)
        object.__setattr__(self, "subdirectory", subdirectory)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        return cls(
            path=_get_required(d, str, "path"),
            editable=_get(d, bool, "editable"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass(frozen=True)
class PackageArchive:
    url: Optional[str]  # = None
    path: Optional[str]  # = None
    size: Optional[int]  # = None
    upload_time: Optional[datetime]  # = None
    hashes: Mapping[str, str]
    subdirectory: Optional[str] = None

    def __init__(
        self,
        *,
        hashes: Mapping[str, str],
        url: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
        upload_time: Optional[datetime] = None,
        subdirectory: Optional[str] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "upload_time", upload_time)
        object.__setattr__(self, "hashes", hashes)
        object.__setattr__(self, "subdirectory", subdirectory)
        # __post_init__ in Python 3.10+
        _validate_path_url(self.path, self.url)
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        return cls(
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            upload_time=_get(d, datetime, "upload-time"),
            hashes=_get_required(d, Mapping, "hashes"),  # type: ignore[type-abstract]
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass(frozen=True)
class PackageSdist:
    name: str
    upload_time: Optional[datetime]  # = None
    url: Optional[str]  # = None
    path: Optional[str]  # = None
    size: Optional[int]  # = None
    hashes: Mapping[str, str]

    def __init__(
        self,
        *,
        name: str,
        hashes: Mapping[str, str],
        upload_time: Optional[datetime] = None,
        url: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "upload_time", upload_time)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "hashes", hashes)
        # __post_init__ in Python 3.10+
        _validate_path_url(self.path, self.url)
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        return cls(
            name=_get_required(d, str, "name"),
            upload_time=_get(d, datetime, "upload-time"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, Mapping, "hashes"),  # type: ignore[type-abstract]
        )


@dataclass(frozen=True)
class PackageWheel:
    name: str
    upload_time: Optional[datetime]  # = None
    url: Optional[str]  # = None
    path: Optional[str]  # = None
    size: Optional[int]  # = None
    hashes: Mapping[str, str]

    def __init__(
        self,
        *,
        name: str,
        hashes: Mapping[str, str],
        upload_time: Optional[datetime] = None,
        url: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "upload_time", upload_time)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "hashes", hashes)
        # __post_init__ in Python 3.10+
        _validate_path_url(self.path, self.url)
        _validate_hashes(self.hashes)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        wheel = cls(
            name=_get_required(d, str, "name"),
            upload_time=_get(d, datetime, "upload-time"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, Mapping, "hashes"),  # type: ignore[type-abstract]
        )
        return wheel


@dataclass(frozen=True)
class Package:
    name: str
    version: Optional[Version] = None
    marker: Optional[Marker] = None
    requires_python: Optional[SpecifierSet] = None
    dependencies: Optional[Sequence[Mapping[str, Any]]] = None
    vcs: Optional[PackageVcs] = None
    directory: Optional[PackageDirectory] = None
    archive: Optional[PackageArchive] = None
    index: Optional[str] = None
    sdist: Optional[PackageSdist] = None
    wheels: Optional[Sequence[PackageWheel]] = None
    attestation_identities: Optional[Sequence[Mapping[str, Any]]] = None
    tool: Optional[Mapping[str, Any]] = None

    def __init__(
        self,
        *,
        name: str,
        version: Optional[Version] = None,
        marker: Optional[Marker] = None,
        requires_python: Optional[SpecifierSet] = None,
        dependencies: Optional[Sequence[Mapping[str, Any]]] = None,
        vcs: Optional[PackageVcs] = None,
        directory: Optional[PackageDirectory] = None,
        archive: Optional[PackageArchive] = None,
        index: Optional[str] = None,
        sdist: Optional[PackageSdist] = None,
        wheels: Optional[Sequence[PackageWheel]] = None,
        attestation_identities: Optional[Sequence[Mapping[str, Any]]] = None,
        tool: Optional[Mapping[str, Any]] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "marker", marker)
        object.__setattr__(self, "requires_python", requires_python)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "vcs", vcs)
        object.__setattr__(self, "directory", directory)
        object.__setattr__(self, "archive", archive)
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "sdist", sdist)
        object.__setattr__(self, "wheels", wheels)
        object.__setattr__(self, "attestation_identities", attestation_identities)
        object.__setattr__(self, "tool", tool)
        # __post_init__ in Python 3.10+
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
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        package = cls(
            name=_get_required(d, str, "name"),
            version=_get_as(d, str, Version, "version"),
            requires_python=_get_as(d, str, SpecifierSet, "requires-python"),
            dependencies=_get_list(d, Mapping, "dependencies"),  # type: ignore[type-abstract]
            marker=_get_as(d, str, Marker, "marker"),
            vcs=_get_object(d, PackageVcs, "vcs"),
            directory=_get_object(d, PackageDirectory, "directory"),
            archive=_get_object(d, PackageArchive, "archive"),
            index=_get(d, str, "index"),
            sdist=_get_object(d, PackageSdist, "sdist"),
            wheels=_get_list_of_objects(d, PackageWheel, "wheels"),
            attestation_identities=_get_list(d, Mapping, "attestation-identities"),  # type: ignore[type-abstract]
            tool=_get(d, Mapping, "tool"),  # type: ignore[type-abstract]
        )
        return package

    @property
    def is_direct(self) -> bool:
        return not (self.sdist or self.wheels)


@dataclass(frozen=True)
class Pylock:
    lock_version: Version
    environments: Optional[Sequence[Marker]]  # = None
    requires_python: Optional[SpecifierSet]  # = None
    extras: Sequence[str]  # = dataclasses.field(default_factory=list)
    dependency_groups: Sequence[str]  # = dataclasses.field(default_factory=list)
    default_groups: Sequence[str]  # = dataclasses.field(default_factory=list)
    created_by: str
    packages: Sequence[Package]
    tool: Optional[Mapping[str, Any]] = None

    def __init__(
        self,
        *,
        lock_version: Version,
        created_by: str,
        packages: Sequence[Package],
        environments: Optional[Sequence[Marker]] = None,
        requires_python: Optional[SpecifierSet] = None,
        extras: Optional[Sequence[str]] = None,
        dependency_groups: Optional[Sequence[str]] = None,
        default_groups: Optional[Sequence[str]] = None,
        tool: Optional[Mapping[str, Any]] = None,
    ) -> None:
        # In Python 3.10+ make dataclass kw_only=True and remove __init__
        object.__setattr__(self, "lock_version", lock_version)
        object.__setattr__(self, "environments", environments)
        object.__setattr__(self, "requires_python", requires_python)
        object.__setattr__(self, "extras", extras or [])
        object.__setattr__(self, "dependency_groups", dependency_groups or [])
        object.__setattr__(self, "default_groups", default_groups or [])
        object.__setattr__(self, "created_by", created_by)
        object.__setattr__(self, "packages", packages)
        object.__setattr__(self, "tool", tool)
        # __post_init__ in Python 3.10+
        if self.lock_version < Version("1") or self.lock_version >= Version("2"):
            raise PylockUnsupportedVersionError(
                f"pylock version {self.lock_version} is not supported"
            )
        if self.lock_version > Version("1.0"):
            logging.warning(
                "pylock minor version %s is not supported", self.lock_version
            )

    def to_dict(self) -> Mapping[str, Any]:
        return dataclasses.asdict(self, dict_factory=_toml_dict_factory)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Self":
        return cls(
            lock_version=_get_required_as(d, str, Version, "lock-version"),
            environments=_get_list_as(d, str, Marker, "environments"),
            extras=_get_list(d, str, "extras") or [],
            dependency_groups=_get_list(d, str, "dependency-groups") or [],
            default_groups=_get_list(d, str, "default-groups") or [],
            created_by=_get_required(d, str, "created-by"),
            requires_python=_get_as(d, str, SpecifierSet, "requires-python"),
            packages=_get_required_list_of_objects(d, Package, "packages"),
            tool=_get(d, Mapping, "tool"),  # type: ignore[type-abstract]
        )
