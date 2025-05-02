import dataclasses
import logging
import re
import sys
from dataclasses import dataclass
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

from pip._vendor import tomli_w
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

from pip._internal.models.direct_url import ArchiveInfo, DirInfo, VcsInfo
from pip._internal.models.link import Link
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.urls import url_to_path

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from pip._vendor.typing_extensions import Self

T = TypeVar("T")
T2 = TypeVar("T2")


class FromDictProtocol(Protocol):
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        pass


FromDictProtocolT = TypeVar("FromDictProtocolT", bound=FromDictProtocol)

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
        if value is not None
    }


def _get(d: Dict[str, Any], expected_type: Type[T], key: str) -> Optional[T]:
    """Get value from dictionary and verify expected type."""
    value = d.get(key)
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise PylockValidationError(
            f"{key} has unexpected type {type(value)} (expected {expected_type})"
        )
    return value


def _get_required(d: Dict[str, Any], expected_type: Type[T], key: str) -> T:
    """Get required value from dictionary and verify expected type."""
    value = _get(d, expected_type, key)
    if value is None:
        raise PylockRequiredKeyError(key)
    return value


def _get_as(
    d: Dict[str, Any], expected_type: Type[T], target_type: Type[T2], key: str
) -> Optional[T2]:
    """Get value from dictionary, verify expected type, convert to target type.

    This assumes the target_type constructor accepts the value.
    """
    value = _get(d, expected_type, key)
    if value is None:
        return None
    try:
        return target_type(value)  # type: ignore[call-arg]
    except Exception as e:
        raise PylockValidationError(f"Error parsing value of {key!r}: {e}") from e


def _get_required_as(
    d: Dict[str, Any], expected_type: Type[T], target_type: Type[T2], key: str
) -> T2:
    """Get required value from dictionary, verify expected type,
    convert to target type."""
    value = _get_as(d, expected_type, target_type, key)
    if value is None:
        raise PylockRequiredKeyError(key)
    return value


def _get_list_as(
    d: Dict[str, Any], expected_type: Type[T], target_type: Type[T2], key: str
) -> Optional[List[T2]]:
    """Get list value from dictionary and verify expected items type."""
    value = _get(d, list, key)
    if value is None:
        return None
    result = []
    for i, item in enumerate(value):
        if not isinstance(item, expected_type):
            raise PylockValidationError(
                f"Item {i} of {key} has unpexpected type {type(item)} "
                f"(expected {expected_type})"
            )
        try:
            result.append(target_type(item))  # type: ignore[call-arg]
        except Exception as e:
            raise PylockValidationError(
                f"Error parsing item {i} of {key!r}: {e}"
            ) from e
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
        raise PylockValidationError(f"Error parsing value of {key!r}: {e}") from e


def _get_list_of_objects(
    d: Dict[str, Any], target_type: Type[FromDictProtocolT], key: str
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
            result.append(target_type.from_dict(item))
        except Exception as e:
            raise PylockValidationError(
                f"Error parsing item {i} of {key!r}: {e}"
            ) from e
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


class PylockValidationError(Exception):
    pass


class PylockRequiredKeyError(PylockValidationError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Missing required key {key!r}")
        self.key = key


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
        # TODO validate supported vcs type
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
    # (not supported) upload_time: Optional[datetime]
    hashes: Dict[str, str]
    subdirectory: Optional[str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for archive package")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, dict, "hashes"),
            subdirectory=_get(d, str, "subdirectory"),
        )


@dataclass
class PackageSdist:
    name: str
    # (not supported) upload_time: Optional[datetime]
    url: Optional[str]
    path: Optional[str]
    size: Optional[int]
    hashes: Dict[str, str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for sdist package")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            name=_get_required(d, str, "name"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, dict, "hashes"),
        )


@dataclass
class PackageWheel:
    name: str
    # (not supported) upload_time: Optional[datetime]
    url: Optional[str]
    path: Optional[str]
    size: Optional[int]
    hashes: Dict[str, str]

    def __post_init__(self) -> None:
        if not self.path and not self.url:
            raise PylockValidationError("No path nor url set for wheel package")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        wheel = cls(
            name=_get_required(d, str, "name"),
            url=_get(d, str, "url"),
            path=_get(d, str, "path"),
            size=_get(d, int, "size"),
            hashes=_get_required(d, dict, "hashes"),
        )
        return wheel


@dataclass
class Package:
    name: str
    version: Optional[Version] = None
    marker: Optional[Marker] = None
    requires_python: Optional[SpecifierSet] = None
    # (not supported) dependencies
    vcs: Optional[PackageVcs] = None
    directory: Optional[PackageDirectory] = None
    archive: Optional[PackageArchive] = None
    # (not supported) index: Optional[str]
    sdist: Optional[PackageSdist] = None
    wheels: Optional[List[PackageWheel]] = None
    # (not supported) attestation_identities: Optional[List[Dict[str, Any]]]
    # (not supported) tool: Optional[Dict[str, Any]]

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
            marker=_get_as(d, str, Marker, "marker"),
            vcs=_get_object(d, PackageVcs, "vcs"),
            directory=_get_object(d, PackageDirectory, "directory"),
            archive=_get_object(d, PackageArchive, "archive"),
            sdist=_get_object(d, PackageSdist, "sdist"),
            wheels=_get_list_of_objects(d, PackageWheel, "wheels"),
        )
        return package

    @classmethod
    def from_install_requirement(
        cls, ireq: InstallRequirement, base_dir: Path
    ) -> "Self":
        base_dir = base_dir.resolve()
        dist = ireq.get_dist()
        download_info = ireq.download_info
        assert download_info
        package_version = None
        package_vcs = None
        package_directory = None
        package_archive = None
        package_sdist = None
        package_wheels = None
        if ireq.is_direct:
            if isinstance(download_info.info, VcsInfo):
                package_vcs = PackageVcs(
                    type=download_info.info.vcs,
                    url=download_info.url,
                    path=None,
                    requested_revision=download_info.info.requested_revision,
                    commit_id=download_info.info.commit_id,
                    subdirectory=download_info.subdirectory,
                )
            elif isinstance(download_info.info, DirInfo):
                package_directory = PackageDirectory(
                    path=(
                        Path(url_to_path(download_info.url))
                        .resolve()
                        .relative_to(base_dir)
                        .as_posix()
                    ),
                    editable=(
                        download_info.info.editable
                        if download_info.info.editable
                        else None
                    ),
                    subdirectory=download_info.subdirectory,
                )
            elif isinstance(download_info.info, ArchiveInfo):
                if not download_info.info.hashes:
                    raise NotImplementedError()
                package_archive = PackageArchive(
                    url=download_info.url,
                    path=None,
                    size=None,  # not supported
                    hashes=download_info.info.hashes,
                    subdirectory=download_info.subdirectory,
                )
            else:
                # should never happen
                raise NotImplementedError()
        else:
            package_version = dist.version
            if isinstance(download_info.info, ArchiveInfo):
                if not download_info.info.hashes:
                    raise NotImplementedError()
                link = Link(download_info.url)
                if link.is_wheel:
                    package_wheels = [
                        PackageWheel(
                            name=link.filename,
                            url=download_info.url,
                            path=None,
                            size=None,  # not supported
                            hashes=download_info.info.hashes,
                        )
                    ]
                else:
                    package_sdist = PackageSdist(
                        name=link.filename,
                        url=download_info.url,
                        path=None,
                        size=None,  # not supported
                        hashes=download_info.info.hashes,
                    )
            else:
                # should never happen
                raise NotImplementedError()
        return cls(
            name=dist.canonical_name,
            version=package_version,
            marker=None,  # not supported
            requires_python=None,  # not supported
            vcs=package_vcs,
            directory=package_directory,
            archive=package_archive,
            sdist=package_sdist,
            wheels=package_wheels,
        )


@dataclass
class Pylock:
    lock_version: Version
    environments: Optional[List[Marker]]
    requires_python: Optional[SpecifierSet]
    # (not supported) extras: List[str] = []
    # (not supported) dependency_groups: List[str] = []
    created_by: str
    packages: List[Package]
    # (not supported) tool: Optional[Dict[str, Any]]

    def __post_init__(self) -> None:
        if self.lock_version < Version("1") or self.lock_version >= Version("2"):
            raise PylockUnsupportedVersionError(
                f"pylock version {self.lock_version} is not supported"
            )
        if self.lock_version > Version("1.0"):
            logging.warning(
                "pylock minor version %s is not supported", self.lock_version
            )

    def as_toml(self) -> str:
        return tomli_w.dumps(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self, dict_factory=_toml_dict_factory)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Self":
        return cls(
            lock_version=_get_required_as(d, str, Version, "lock-version"),
            environments=_get_list_as(d, str, Marker, "environments"),
            created_by=_get_required(d, str, "created-by"),
            requires_python=_get_as(d, str, SpecifierSet, "requires-python"),
            packages=_get_required_list_of_objects(d, Package, "packages"),
        )

    @classmethod
    def from_install_requirements(
        cls, install_requirements: Iterable[InstallRequirement], base_dir: Path
    ) -> "Self":
        return cls(
            lock_version=Version("1.0"),
            environments=None,  # not supported
            requires_python=None,  # not supported
            created_by="pip",
            packages=sorted(
                (
                    Package.from_install_requirement(ireq, base_dir)
                    for ireq in install_requirements
                ),
                key=lambda p: p.name,
            ),
        )
