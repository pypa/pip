""" PEP 610 """
import abc
import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Iterable, Optional, Type, TypeVar

__all__ = [
    "DirectUrl",
    "DirectUrlValidationError",
    "DirInfo",
    "ArchiveInfo",
    "VcsInfo",
]

T = TypeVar("T")

DIRECT_URL_METADATA_NAME = "direct_url.json"
ENV_VAR_RE = re.compile(r"^\$\{[A-Za-z0-9-_]+\}(:\$\{[A-Za-z0-9-_]+\})?$")


class DirectUrlValidationError(Exception):
    pass


def _get(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> Optional[T]:
    """Get value from dictionary and verify expected type."""
    if key not in d:
        return default
    value = d[key]
    if not isinstance(value, expected_type):
        raise DirectUrlValidationError(
            "{!r} has unexpected type for {} (expected {})".format(
                value, key, expected_type
            )
        )
    return value


def _get_required(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> T:
    value = _get(d, expected_type, key, default)
    if value is None:
        raise DirectUrlValidationError(f"{key} must have a value")
    return value


def _filter_none(**kwargs: Any) -> Dict[str, Any]:
    """Make dict excluding None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


class InfoType(metaclass=abc.ABCMeta):
    """Superclass for the types of metadata that can be stored within a "direct URL"."""

    name: ClassVar[str]

    @classmethod
    @abc.abstractmethod
    def _from_dict(cls: Type[T], d: Optional[Dict[str, Any]]) -> Optional[T]:
        """Parse an instance of this class from a JSON-serializable dict."""

    @abc.abstractmethod
    def _to_dict(self) -> Dict[str, Any]:
        """Produce a JSON-serializable dict which can be parsed with `._from_dict()`."""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InfoType":
        """Parse exactly one of the known subclasses from the dict `d`."""
        return _exactly_one_of(
            [
                ArchiveInfo._from_dict(_get(d, dict, "archive_info")),
                DirInfo._from_dict(_get(d, dict, "dir_info")),
                VcsInfo._from_dict(_get(d, dict, "vcs_info")),
            ]
        )


def _exactly_one_of(infos: Iterable[Optional[InfoType]]) -> InfoType:
    infos = list(filter(None, infos))
    if not infos:
        raise DirectUrlValidationError(
            "missing one of archive_info, dir_info, vcs_info"
        )
    if len(infos) > 1:
        raise DirectUrlValidationError(
            "more than one of archive_info, dir_info, vcs_info"
        )
    assert infos[0] is not None
    return infos[0]


@dataclass(frozen=True)
class VcsInfo(InfoType):
    vcs: str
    commit_id: str
    requested_revision: Optional[str] = None
    resolved_revision: Optional[str] = None
    resolved_revision_type: Optional[str] = None

    name: ClassVar[str] = "vcs_info"

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["VcsInfo"]:
        if d is None:
            return None
        return cls(
            vcs=_get_required(d, str, "vcs"),
            commit_id=_get_required(d, str, "commit_id"),
            requested_revision=_get(d, str, "requested_revision"),
        )

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(
            vcs=self.vcs,
            requested_revision=self.requested_revision,
            commit_id=self.commit_id,
        )


@dataclass(frozen=True)
class ArchiveInfo(InfoType):
    hash: Optional[str] = None

    name: ClassVar[str] = "archive_info"

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["ArchiveInfo"]:
        if d is None:
            return None
        return cls(hash=_get(d, str, "hash"))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(hash=self.hash)


@dataclass(frozen=True)
class DirInfo(InfoType):
    editable: bool = False

    name: ClassVar[str] = "dir_info"

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["DirInfo"]:
        if d is None:
            return None
        return cls(editable=_get_required(d, bool, "editable", default=False))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(editable=self.editable or None)


@dataclass(frozen=True)
class DirectUrl:
    url: str
    info: InfoType
    subdirectory: Optional[str] = None

    def _remove_auth_from_netloc(self, netloc: str) -> str:
        if "@" not in netloc:
            return netloc
        user_pass, netloc_no_user_pass = netloc.split("@", 1)
        if (
            isinstance(self.info, VcsInfo)
            and self.info.vcs == "git"
            and user_pass == "git"
        ):
            return netloc
        if ENV_VAR_RE.match(user_pass):
            return netloc
        return netloc_no_user_pass

    @property
    def redacted_url(self) -> str:
        """url with user:password part removed unless it is formed with
        environment variables as specified in PEP 610, or it is ``git``
        in the case of a git URL.
        """
        purl = urllib.parse.urlsplit(self.url)
        netloc = self._remove_auth_from_netloc(purl.netloc)
        surl = urllib.parse.urlunsplit(
            (purl.scheme, netloc, purl.path, purl.query, purl.fragment)
        )
        return surl

    def validate(self) -> None:
        self.from_dict(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DirectUrl":
        return DirectUrl(
            url=_get_required(d, str, "url"),
            subdirectory=_get(d, str, "subdirectory"),
            info=InfoType.from_dict(d),
        )

    def to_dict(self) -> Dict[str, Any]:
        res = _filter_none(
            url=self.redacted_url,
            subdirectory=self.subdirectory,
        )
        res[self.info.name] = self.info._to_dict()
        return res

    @classmethod
    def from_json(cls, s: str) -> "DirectUrl":
        return cls.from_dict(json.loads(s))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def is_local_editable(self) -> bool:
        return isinstance(self.info, DirInfo) and self.info.editable
