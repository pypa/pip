"""Helper for building wheels as would be in test cases.
"""
import csv
import itertools
from base64 import urlsafe_b64encode
from collections import namedtuple
from copy import deepcopy
from email.message import Message
from enum import Enum
from functools import partial
from hashlib import sha256
from io import BytesIO, StringIO
from typing import (
    AnyStr,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from zipfile import ZipFile

from pip._vendor.requests.structures import CaseInsensitiveDict

from pip._internal.metadata import BaseDistribution, MemoryWheel, get_wheel_distribution
from tests.lib.path import Path

# As would be used in metadata
HeaderValue = Union[str, List[str]]


File = namedtuple("File", ["name", "contents"])
Record = namedtuple("Record", ["path", "digest", "size"])


class Default(Enum):
    token = 0


_default = Default.token

T = TypeVar("T")

# A type which may be defaulted.
Defaulted = Union[Default, T]


def ensure_binary(value: AnyStr) -> bytes:
    if isinstance(value, bytes):
        return value
    return value.encode()


def message_from_dict(headers: Dict[str, HeaderValue]) -> Message:
    """Plain key-value pairs are set in the returned message.

    List values are converted into repeated headers in the result.
    """
    message = Message()
    for name, value in headers.items():
        if isinstance(value, list):
            for v in value:
                message[name] = v
        else:
            message[name] = value
    return message


def dist_info_path(name: str, version: str, path: str) -> str:
    return f"{name}-{version}.dist-info/{path}"


def make_metadata_file(
    name: str,
    version: str,
    value: Defaulted[Optional[AnyStr]],
    updates: Defaulted[Dict[str, HeaderValue]],
    body: Defaulted[AnyStr],
) -> Optional[File]:
    if value is None:
        return None

    path = dist_info_path(name, version, "METADATA")

    if value is not _default:
        return File(path, ensure_binary(value))

    metadata = CaseInsensitiveDict(
        {
            "Metadata-Version": "2.1",
            "Name": name,
            "Version": version,
        }
    )
    if updates is not _default:
        metadata.update(updates)

    message = message_from_dict(metadata)
    if body is not _default:
        message.set_payload(body)

    return File(path, message_from_dict(metadata).as_bytes())


def make_wheel_metadata_file(
    name: str,
    version: str,
    value: Defaulted[Optional[AnyStr]],
    tags: Sequence[Tuple[str, str, str]],
    updates: Defaulted[Dict[str, HeaderValue]],
) -> Optional[File]:
    if value is None:
        return None

    path = dist_info_path(name, version, "WHEEL")

    if value is not _default:
        return File(path, ensure_binary(value))

    metadata = CaseInsensitiveDict(
        {
            "Wheel-Version": "1.0",
            "Generator": "pip-test-suite",
            "Root-Is-Purelib": "true",
            "Tag": ["-".join(parts) for parts in tags],
        }
    )

    if updates is not _default:
        metadata.update(updates)

    return File(path, message_from_dict(metadata).as_bytes())


def make_entry_points_file(
    name: str,
    version: str,
    entry_points: Defaulted[Dict[str, List[str]]],
    console_scripts: Defaulted[List[str]],
) -> Optional[File]:
    if entry_points is _default and console_scripts is _default:
        return None

    if entry_points is _default:
        entry_points_data = {}
    else:
        entry_points_data = deepcopy(entry_points)

    if console_scripts is not _default:
        entry_points_data["console_scripts"] = console_scripts

    lines = []
    for section, values in entry_points_data.items():
        lines.append(f"[{section}]")
        lines.extend(values)

    return File(
        dist_info_path(name, version, "entry_points.txt"),
        "\n".join(lines).encode(),
    )


def make_files(files: Dict[str, AnyStr]) -> List[File]:
    return [File(name, ensure_binary(contents)) for name, contents in files.items()]


def make_metadata_files(
    name: str, version: str, files: Dict[str, AnyStr]
) -> List[File]:
    get_path = partial(dist_info_path, name, version)
    return [
        File(get_path(name), ensure_binary(contents))
        for name, contents in files.items()
    ]


def make_data_files(name: str, version: str, files: Dict[str, AnyStr]) -> List[File]:
    data_dir = f"{name}-{version}.data"
    return [
        File(f"{data_dir}/{name}", ensure_binary(contents))
        for name, contents in files.items()
    ]


def urlsafe_b64encode_nopad(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def digest(contents: bytes) -> str:
    return "sha256={}".format(urlsafe_b64encode_nopad(sha256(contents).digest()))


def record_file_maker_wrapper(
    name: str,
    version: str,
    files: Iterable[File],
    record: Defaulted[Optional[AnyStr]],
) -> Iterable[File]:
    records: List[Record] = []
    for file in files:
        records.append(
            Record(file.name, digest(file.contents), str(len(file.contents)))
        )
        yield file

    if record is None:
        return

    record_path = dist_info_path(name, version, "RECORD")

    if record is not _default:
        yield File(record_path, ensure_binary(record))
        return

    records.append(Record(record_path, "", ""))

    with StringIO(newline="") as buf:
        writer = csv.writer(buf)
        for r in records:
            writer.writerow(r)
        contents = buf.getvalue().encode("utf-8")

    yield File(record_path, contents)


def wheel_name(
    name: str,
    version: str,
    pythons: Iterable[str],
    abis: Iterable[str],
    platforms: Iterable[str],
) -> str:
    stem = "-".join(
        [
            name,
            version,
            ".".join(pythons),
            ".".join(abis),
            ".".join(platforms),
        ]
    )
    return f"{stem}.whl"


class WheelBuilder:
    """A wheel that can be saved or converted to several formats."""

    def __init__(self, name: str, files: Iterable[File]) -> None:
        self._name = name
        self._files = files

    def save_to_dir(self, path: Union[Path, str]) -> str:
        """Generate wheel file with correct name and save into the provided
        directory.

        :returns the wheel file path
        """
        p = Path(path) / self._name
        p.write_bytes(self.as_bytes())
        return str(p)

    def save_to(self, path: Union[Path, str]) -> str:
        """Generate wheel file, saving to the provided path. Any parent
        directories must already exist.

        :returns the wheel file path
        """
        path = Path(path)
        path.write_bytes(self.as_bytes())
        return str(path)

    def as_bytes(self) -> bytes:
        with BytesIO() as buf:
            with ZipFile(buf, "w") as z:
                for file in self._files:
                    z.writestr(file.name, file.contents)
            return buf.getvalue()

    def as_zipfile(self) -> ZipFile:
        return ZipFile(BytesIO(self.as_bytes()))

    def as_distribution(self, name: str) -> BaseDistribution:
        stream = BytesIO(self.as_bytes())
        return get_wheel_distribution(MemoryWheel(self._name, stream), name)


def make_wheel(
    name: str,
    version: str,
    wheel_metadata: Defaulted[Optional[AnyStr]] = _default,
    wheel_metadata_updates: Defaulted[Dict[str, HeaderValue]] = _default,
    metadata: Defaulted[Optional[AnyStr]] = _default,
    metadata_body: Defaulted[AnyStr] = _default,
    metadata_updates: Defaulted[Dict[str, HeaderValue]] = _default,
    extra_files: Defaulted[Dict[str, AnyStr]] = _default,
    extra_metadata_files: Defaulted[Dict[str, AnyStr]] = _default,
    extra_data_files: Defaulted[Dict[str, AnyStr]] = _default,
    console_scripts: Defaulted[List[str]] = _default,
    entry_points: Defaulted[Dict[str, List[str]]] = _default,
    record: Defaulted[Optional[AnyStr]] = _default,
) -> WheelBuilder:
    """
    Helper function for generating test wheels which are compliant by default.

    Examples:

    ```
    # Basic wheel, which will have valid metadata, RECORD, etc
    make_wheel(name="foo", version="0.1.0")
    # Wheel with custom metadata
    make_wheel(
        name="foo",
        version="0.1.0",
        metadata_updates={
            # Overrides default
            "Name": "hello",
            # Expands into separate Requires-Dist entries
            "Requires-Dist": ["a == 1.0", "b == 2.0; sys_platform == 'win32'"],
        },
    )
    ```

    After specifying the wheel, it can be consumed in several ways:

    ```
    # Normal case, valid wheel we want pip to pick up.
    make_wheel(...).save_to_dir(tmpdir)
    # For a test case, to check that pip validates contents against wheel name.
    make_wheel(name="simple", ...).save_to(tmpdir / "notsimple-...")
    # In-memory, for unit tests.
    z = make_wheel(...).as_zipfile()
    ```

    Below, any unicode value provided for AnyStr will be encoded as utf-8.

    :param name: name of the distribution, propagated to the .dist-info
        directory, METADATA, and wheel file name
    :param version: version of the distribution, propagated to the .dist-info
        directory, METADATA, and wheel file name
    :param wheel_metadata: if provided and None, then no WHEEL metadata file
        is generated; else if a string then sets the content of the WHEEL file
    :param wheel_metadata_updates: override the default WHEEL metadata fields,
        ignored if wheel_metadata is provided
    :param metadata: if provided and None, then no METADATA file is generated;
        else if a string then sets the content of the METADATA file
    :param metadata_body: sets the value of the body text in METADATA, ignored
        if metadata is provided
    :param metadata_updates: override the default METADATA fields,
        ignored if metadata is provided
    :param extra_files: map from path to file contents for additional files to
        be put in the wheel
    :param extra_metadata_files: map from path (relative to .dist-info) to file
        contents for additional files to be put in the wheel
    :param extra_data_files: map from path (relative to .data) to file contents
        for additional files to be put in the wheel
    :param console_scripts: list of console scripts text to be put into
        entry_points.txt - overrides any value set in entry_points
    :param entry_points:
    :param record: if provided and None, then no RECORD file is generated;
        else if a string then sets the content of the RECORD file
    """
    pythons = ["py2", "py3"]
    abis = ["none"]
    platforms = ["any"]
    tags = list(itertools.product(pythons, abis, platforms))

    possible_files = [
        make_metadata_file(name, version, metadata, metadata_updates, metadata_body),
        make_wheel_metadata_file(
            name, version, wheel_metadata, tags, wheel_metadata_updates
        ),
        make_entry_points_file(name, version, entry_points, console_scripts),
    ]

    if extra_files is not _default:
        possible_files.extend(make_files(extra_files))

    if extra_metadata_files is not _default:
        possible_files.extend(make_metadata_files(name, version, extra_metadata_files))

    if extra_data_files is not _default:
        possible_files.extend(make_data_files(name, version, extra_data_files))

    actual_files = filter(None, possible_files)

    files_and_record_file = record_file_maker_wrapper(
        name, version, actual_files, record
    )
    wheel_file_name = wheel_name(name, version, pythons, abis, platforms)

    return WheelBuilder(wheel_file_name, files_and_record_file)
