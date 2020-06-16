"""
Extract files from remote zip archives without downloading more than a few
extra KB.
"""

import re
import struct
import zlib
from collections import namedtuple

from pip._vendor.six import PY3

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .httpfile import BytesRangeRequest
from .httpfile import Context as HttpContext
from .httpfile import Size

if MYPY_CHECK_RUNNING:
    from typing import Any, Optional

    if PY3:
        ZipMemberPattern = re.Pattern[bytes]
    else:
        ZipMemberPattern = Any


# From https://stackoverflow.com/a/1089787/2518889:
def _inflate(data):
    # type: (bytes) -> bytes
    decompress = zlib.decompressobj(-zlib.MAX_WBITS)
    inflated = decompress.decompress(data)
    inflated += decompress.flush()
    return inflated


def _decode_4_byte_unsigned(byte_string):
    # type: (bytes) -> int
    """Unpack as a little-endian unsigned long."""
    assert isinstance(byte_string, bytes) and len(byte_string) == 4
    return struct.unpack("<L", byte_string)[0]


def _decode_2_byte_unsigned(byte_string):
    # type: (bytes) -> int
    """Unpack as a little-endian unsigned short."""
    assert isinstance(byte_string, bytes) and len(byte_string) == 2
    return struct.unpack("<H", byte_string)[0]


class ZipMemberNameMatcher(namedtuple('ZipMemberNameMatcher', ['pattern'])):

    def __new__(cls, pattern):
        # type: (ZipMemberPattern) -> ZipMemberNameMatcher
        # Matching file names in zip files without the zipfile library requires
        # a binary regex, not "text".
        assert isinstance(pattern.pattern, bytes)  # type: ignore
        return super(ZipMemberNameMatcher, cls).__new__(cls, pattern)


class ZipFileExtractionRequest(namedtuple('ZipFileExtractionRequest', [
        'http_file',
        'member_pattern',
])):
    pass


class Context(object):

    def __init__(self, http_context=None):
        # type: (Optional[HttpContext]) -> None
        self.http_context = http_context or HttpContext()

    _ABSOLUTE_MINIMUM_CENTRAL_DIRECTORY_SIZE = 2000
    _CENTRAL_DIRECTORY_MAX_SIZE_FACTOR = 0.01

    @classmethod
    def _estimate_minimum_central_directory_record_size(cls, size):
        # type: (Size) -> Size
        lower_bound = int(
            max(
                cls._ABSOLUTE_MINIMUM_CENTRAL_DIRECTORY_SIZE,
                size.size * cls._CENTRAL_DIRECTORY_MAX_SIZE_FACTOR,
            )
        )
        actual_record_size = min(lower_bound, size.size)
        return Size(actual_record_size)

    def extract_zip_member_shallow(self, request):
        # type: (ZipFileExtractionRequest) -> bytes
        http_file = request.http_file
        full_size = http_file.size

        estimated_directory_record_size = (
            self._estimate_minimum_central_directory_record_size(full_size))
        central_directory_range_request = BytesRangeRequest(
            start=(full_size - estimated_directory_record_size), end=full_size,
        )

        zip_tail = self.http_context.range_request(
            http_file, central_directory_range_request
        )

        filename_in_central_dir_header = request.member_pattern.pattern.search(
            zip_tail)

        assert filename_in_central_dir_header is not None
        matched_filename = filename_in_central_dir_header.group(0)

        filename_start = filename_in_central_dir_header.start()
        offset_start = filename_start - 4
        encoded_offset_for_local_file = zip_tail[offset_start:filename_start]
        local_file_offset = _decode_4_byte_unsigned(
            encoded_offset_for_local_file)

        local_file_header_range_request = BytesRangeRequest(
            start=Size(local_file_offset + 18),
            end=Size(local_file_offset + 30),
        )
        file_header_no_filename = self.http_context.range_request(
            http_file, local_file_header_range_request
        )

        compressed_size = _decode_4_byte_unsigned(
            file_header_no_filename[:4])
        uncompressed_size = _decode_4_byte_unsigned(
            file_header_no_filename[4:8])
        file_name_length = _decode_2_byte_unsigned(
            file_header_no_filename[8:10])
        assert file_name_length == (len(matched_filename) - 2)
        extra_field_length = _decode_2_byte_unsigned(
            file_header_no_filename[10:12])

        compressed_start = (
            local_file_offset + 30 + file_name_length + extra_field_length
        )
        compressed_end = compressed_start + compressed_size

        compressed_file_range_request = BytesRangeRequest(
            start=Size(compressed_start), end=Size(compressed_end),
        )
        compressed_file = self.http_context.range_request(
            http_file, compressed_file_range_request
        )

        uncompressed_file_contents = _inflate(compressed_file)
        assert len(uncompressed_file_contents) == uncompressed_size

        return uncompressed_file_contents
