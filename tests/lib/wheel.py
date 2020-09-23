"""Helper for building wheels as would be in test cases.
"""
import itertools
from base64 import urlsafe_b64encode
from collections import namedtuple
from copy import deepcopy
from email.message import Message
from enum import Enum
from functools import partial
from hashlib import sha256
from io import BytesIO, StringIO
from zipfile import ZipFile

import csv23
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.six import ensure_binary, ensure_text, iteritems

from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from tests.lib.path import Path

if MYPY_CHECK_RUNNING:
    from typing import (
        AnyStr,
        Callable,
        Dict,
        Iterable,
        List,
        Optional,
        Sequence,
        Tuple,
        TypeVar,
        Union,
    )

    # path, digest, size
    RecordLike = Tuple[str, str, str]
    RecordCallback = Callable[
        [List["Record"]], Union[str, bytes, List[RecordLike]]
    ]
    # As would be used in metadata
    HeaderValue = Union[str, List[str]]


File = namedtuple("File", ["name", "contents"])
Record = namedtuple("Record", ["path", "digest", "size"])


class Default(Enum):
    token = 0


_default = Default.token


if MYPY_CHECK_RUNNING:
    T = TypeVar("T")

    class Defaulted(Union[Default, T]):
        """A type which may be defaulted.
        """
        pass


def message_from_dict(headers):
    # type: (Dict[str, HeaderValue]) -> Message
    """Plain key-value pairs are set in the returned message.

    List values are converted into repeated headers in the result.
    """
    message = Message()
    for name, value in iteritems(headers):
        if isinstance(value, list):
            for v in value:
                message[name] = v
        else:
            message[name] = value
    return message


def dist_info_path(name, version, path):
    # type: (str, str, str) -> str
    return "{}-{}.dist-info/{}".format(name, version, path)


def make_metadata_file(
    name,  # type: str
    version,  # type: str
    value,  # type: Defaulted[Optional[AnyStr]]
    updates,  # type: Defaulted[Dict[str, HeaderValue]]
    body,  # type: Defaulted[AnyStr]
):
    # type: () -> File
    if value is None:
        return None

    path = dist_info_path(name, version, "METADATA")

    if value is not _default:
        return File(path, ensure_binary(value))

    metadata = CaseInsensitiveDict({
        "Metadata-Version": "2.1",
        "Name": name,
        "Version": version,
    })
    if updates is not _default:
        metadata.update(updates)

    message = message_from_dict(metadata)
    if body is not _default:
        message.set_payload(body)

    return File(path, ensure_binary(message_from_dict(metadata).as_string()))


def make_wheel_metadata_file(
    name,  # type: str
    version,  # type: str
    value,  # type: Defaulted[Optional[AnyStr]]
    tags,  # type: Sequence[Tuple[str, str, str]]
    updates,  # type: Defaulted[Dict[str, HeaderValue]]
):
    # type: (...) -> Optional[File]
    if value is None:
        return None

    path = dist_info_path(name, version, "WHEEL")

    if value is not _default:
        return File(path, ensure_binary(value))

    metadata = CaseInsensitiveDict({
        "Wheel-Version": "1.0",
        "Generator": "pip-test-suite",
        "Root-Is-Purelib": "true",
        "Tag": ["-".join(parts) for parts in tags],
    })

    if updates is not _default:
        metadata.update(updates)

    return File(path, ensure_binary(message_from_dict(metadata).as_string()))


def make_entry_points_file(
    name,  # type: str
    version,  # type: str
    entry_points,  # type: Defaulted[Dict[str, List[str]]]
    console_scripts,  # type: Defaulted[List[str]]
):
    # type: (...) -> Optional[File]
    if entry_points is _default and console_scripts is _default:
        return None

    if entry_points is _default:
        entry_points_data = {}
    else:
        entry_points_data = deepcopy(entry_points)

    if console_scripts is not _default:
        entry_points_data["console_scripts"] = console_scripts

    lines = []
    for section, values in iteritems(entry_points_data):
        lines.append("[{}]".format(section))
        lines.extend(values)

    return File(
        dist_info_path(name, version, "entry_points.txt"),
        ensure_binary("\n".join(lines)),
    )


def make_files(files):
    # type: (Dict[str, AnyStr]) -> List[File]
    return [
        File(name, ensure_binary(contents))
        for name, contents in iteritems(files)
    ]


def make_metadata_files(name, version, files):
    # type: (str, str, Dict[str, AnyStr]) -> List[File]
    get_path = partial(dist_info_path, name, version)
    return [
        File(get_path(name), ensure_binary(contents))
        for name, contents in iteritems(files)
    ]


def make_data_files(name, version, files):
    # type: (str, str, Dict[str, AnyStr]) -> List[File]
    data_dir = "{}-{}.data".format(name, version)
    return [
        File("{}/{}".format(data_dir, name), ensure_binary(contents))
        for name, contents in iteritems(files)
    ]


def urlsafe_b64encode_nopad(data):
    # type: (bytes) -> str
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def digest(contents):
    # type: (bytes) -> str
    return "sha256={}".format(
        urlsafe_b64encode_nopad(sha256(contents).digest())
    )


def record_file_maker_wrapper(
    name,  # type: str
    version,  # type: str
    files,  # type: List[File]
    record,  # type: Defaulted[Optional[AnyStr]]
    record_callback,  # type: Defaulted[RecordCallback]
):
    # type: (...) -> Iterable[File]
    records = []  # type: List[Record]
    for file in files:
        records.append(
            Record(
                file.name, digest(file.contents), str(len(file.contents))
            )
        )
        yield file

    if record is None:
        return

    record_path = dist_info_path(name, version, "RECORD")

    if record is not _default:
        yield File(record_path, ensure_binary(record))
        return

    records.append(Record(record_path, "", ""))

    if record_callback is not _default:
        records = record_callback(records)

    with StringIO(newline=u"") as buf:
        writer = csv23.writer(buf)
        for record in records:
            writer.writerow(map(ensure_text, record))
        contents = buf.getvalue().encode("utf-8")

    yield File(record_path, contents)


def wheel_name(name, version, pythons, abis, platforms):
    # type: (str, str, str, str, str) -> str
    stem = "-".join([
        name,
        version,
        ".".join(pythons),
        ".".join(abis),
        ".".join(platforms),
    ])
    return "{}.whl".format(stem)


class WheelBuilder(object):
    """A wheel that can be saved or converted to several formats.
    """

    def __init__(self, name, files):
        # type: (str, List[File]) -> None
        self._name = name
        self._files = files

    def save_to_dir(self, path):
        # type: (Union[Path, str]) -> str
        """Generate wheel file with correct name and save into the provided
        directory.

        :returns the wheel file path
        """
        path = Path(path) / self._name
        path.write_bytes(self.as_bytes())
        return str(path)

    def save_to(self, path):
        # type: (Union[Path, str]) -> str
        """Generate wheel file, saving to the provided path. Any parent
        directories must already exist.

        :returns the wheel file path
        """
        path = Path(path)
        path.write_bytes(self.as_bytes())
        return str(path)

    def as_bytes(self):
        # type: () -> bytes
        with BytesIO() as buf:
            with ZipFile(buf, "w") as z:
                for file in self._files:
                    z.writestr(file.name, file.contents)
            return buf.getvalue()

    def as_zipfile(self):
        # type: () -> ZipFile
        return ZipFile(BytesIO(self.as_bytes()))


def make_wheel(
    name,  # type: str
    version,  # type: str
    wheel_metadata=_default,  # type: Defaulted[Optional[AnyStr]]
    wheel_metadata_updates=_default,  # type: Defaulted[Dict[str, HeaderValue]]
    metadata=_default,  # type: Defaulted[Optional[AnyStr]]
    metadata_body=_default,  # type: Defaulted[AnyStr]
    metadata_updates=_default,  # type: Defaulted[Dict[str, HeaderValue]]
    extra_files=_default,  # type: Defaulted[Dict[str, AnyStr]]
    extra_metadata_files=_default,  # type: Defaulted[Dict[str, AnyStr]]
    extra_data_files=_default,  # type: Defaulted[Dict[str, AnyStr]]
    console_scripts=_default,  # type: Defaulted[List[str]]
    entry_points=_default,  # type: Defaulted[Dict[str, List[str]]]
    record=_default,  # type: Defaulted[Optional[AnyStr]]
    record_callback=_default,  # type: Defaulted[RecordCallback]
):
    # type: (...) -> WheelBuilder
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
    :param record_callback: callback function that receives and can edit the
        records before they are written to RECORD, ignored if record is
        provided
    """
    pythons = ["py2", "py3"]
    abis = ["none"]
    platforms = ["any"]
    tags = list(itertools.product(pythons, abis, platforms))

    possible_files = [
        make_metadata_file(
            name, version, metadata, metadata_updates, metadata_body
        ),
        make_wheel_metadata_file(
            name, version, wheel_metadata, tags, wheel_metadata_updates
        ),
        make_entry_points_file(name, version, entry_points, console_scripts),
    ]

    if extra_files is not _default:
        possible_files.extend(make_files(extra_files))

    if extra_metadata_files is not _default:
        possible_files.extend(
            make_metadata_files(name, version, extra_metadata_files)
        )

    if extra_data_files is not _default:
        possible_files.extend(make_data_files(name, version, extra_data_files))

    actual_files = filter(None, possible_files)

    files_and_record_file = record_file_maker_wrapper(
        name, version, actual_files, record, record_callback
    )
    wheel_file_name = wheel_name(name, version, pythons, abis, platforms)

    return WheelBuilder(wheel_file_name, files_and_record_file)
