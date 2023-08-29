"""Functionality for working with RECORD files."""

from __future__ import annotations

import base64
import binascii
import csv
import dataclasses
import functools
import hashlib
import logging
from typing import TYPE_CHECKING, Dict, List, NewType, NoReturn, Optional, Tuple, cast

from pip._internal.exceptions import PipError
from pip._internal.utils.misc import hash_file

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

logger = logging.getLogger(__name__)

RecordPath = NewType("RecordPath", str)


@dataclasses.dataclass(frozen=True)
class FileHash:
    algorithm_name: str
    digest: bytes

    def __str__(self) -> str:
        encoded_digest = (
            base64.urlsafe_b64encode(self.digest).decode("us-ascii").rstrip("=")
        )
        return f"{self.algorithm_name}={encoded_digest}"


@dataclasses.dataclass(frozen=True)
class FileIntegrity:
    hash: Optional[FileHash]
    size: Optional[int]

    @classmethod
    def generate_for_file(cls, path: str) -> FileIntegrity:
        """
        Create a ``FileIntegrity`` instance for the file at ``path``,
        with the hash and size present.
        """
        hash, size = hash_file(path)
        return cls(FileHash(hash.name, hash.digest()), size)


FileIntegrityMap = Dict[RecordPath, FileIntegrity]


class BrokenRecord(PipError):
    """Invalid RECORD file"""


@functools.lru_cache()
def _get_digest_size(algo: str) -> int:
    return hashlib.new(algo).digest_size


def _parse_record_row(
    row: List[str], file_path: str, row_index: int
) -> Tuple[RecordPath, FileIntegrity]:
    def row_error(message: str) -> NoReturn:
        raise BrokenRecord(f"{file_path}:{row_index+1}: {message}")

    def row_warning(message: str) -> None:
        logger.warning("%s:%d: %s", file_path, row_index + 1, message)

    if len(row) != 3:
        row_error(f"unexpected number of fields ({len(row)}; should be 3)")

    path = cast(RecordPath, row[0])
    algo_and_digest = row[1]
    size_str = row[2]

    if not path:
        row_error("missing path")

    if algo_and_digest:
        algo_and_digest_parts = algo_and_digest.split("=", maxsplit=1)
        if len(algo_and_digest_parts) != 2:
            row_error("invalid hash format")

        algo, digest_str = algo_and_digest_parts

        if algo not in hashlib.algorithms_guaranteed:
            row_error(f"unsupported hash algorithm {algo!a}")

        expected_digest_size = _get_digest_size(algo)
        if expected_digest_size == 0:  # filter out variable-length hashes
            row_error(f"unsupported hash algorithm {algo!a}")

        if digest_str.endswith("="):
            row_warning("unnecessary padding in digest")
            digest_str = digest_str.rstrip("=")

        digest_str += "=" * ((4 - len(digest_str) % 4) % 4)
        try:
            digest = base64.b64decode(digest_str, altchars=b"-_", validate=True)
        except binascii.Error:
            row_error("invalid digest encoding")

        if "+" in digest_str or "/" in digest_str:
            row_warning("digest encoded with non-URL-safe Base64")
            # b64decode will still process these characters, so we don't need
            # to fix up the digest.

        if len(digest) != expected_digest_size:
            row_warning(
                f"unexpected digest length ({len(digest)} bytes;"
                f" should be {expected_digest_size})"
            )

        hash = FileHash(algo, digest)
    else:
        hash = None

    if size_str:
        try:
            size = int(size_str)
        except ValueError:
            row_error(f"non-numeric size value {size_str!a}")

        if size < 0:
            row_error(f"negative file size {size}")
    else:
        size = None

    return path, FileIntegrity(hash, size)


def parse_record(text: str, file_path: str) -> FileIntegrityMap:
    """
    Parses ``text`` as the contents of a RECORD file.
    Raises ``BrokenRecord`` if the file is invalid.

    ``file_path`` is used to report location in warning and error messages.
    """
    integrity_map: FileIntegrityMap = {}

    try:
        reader = csv.reader(text.splitlines())

        for row_index, row in enumerate(reader):
            path, integrity = _parse_record_row(row, file_path, row_index)

            if path in integrity_map:
                if integrity_map[path] == integrity:
                    logging.warning(
                        "%s:%d: duplicate entry for path %a",
                        file_path,
                        row_index + 1,
                        path,
                    )
                else:
                    raise BrokenRecord(
                        f"{file_path}:{row_index+1}:"
                        " inconsistent entry for path {path!a}"
                    )
            integrity_map[path] = integrity
    except csv.Error as e:
        raise BrokenRecord(f"{file_path}: invalid CSV file") from e

    return integrity_map


def serialize_record(integrity_map: FileIntegrityMap, f: SupportsWrite[str]) -> None:
    """
    Writes ``integrity_map`` to ``f`` as a RECORD file.
    """
    writer = csv.writer(f)

    for path, integrity in sorted(integrity_map.items()):
        writer.writerow(
            [
                path,
                str(integrity.hash) if integrity.hash is not None else "",
                str(integrity.size) if integrity.size is not None else "",
            ]
        )
