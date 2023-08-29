"""Tests for RECORD file handling"""

import io
import logging
import os
import textwrap
from pathlib import Path

import pytest

from pip._internal.models.record import (
    BrokenRecord,
    FileHash,
    FileIntegrity,
    RecordPath,
    parse_record,
    serialize_record,
)
from pip._internal.utils.misc import hash_file


class TestFileIntegrityGeneration:
    @pytest.fixture(autouse=True)
    def prep(self, tmp_path: Path) -> None:
        self.test_file = tmp_path.joinpath("hash.file")
        # Want this big enough to trigger the internal read loops.
        self.test_file_len = 2 * 1024 * 1024
        with open(self.test_file, "w") as fp:
            fp.truncate(self.test_file_len)
        self.test_file_hash = bytes.fromhex(
            "5647f05ec18958947d32874eeb788fa396a05d0bab7c1b71f112ceb7e9b31eee"
        )

    def test_hash_file(self) -> None:
        h, length = hash_file(os.fspath(self.test_file))
        assert length == self.test_file_len
        assert h.digest() == self.test_file_hash

    def test_file_integrity_generate(self) -> None:
        integrity = FileIntegrity.generate_for_file(os.fspath(self.test_file))
        assert integrity.size == self.test_file_len
        assert integrity.hash == FileHash("sha256", self.test_file_hash)


def test_parse_valid_record_file(caplog: pytest.LogCaptureFixture) -> None:
    text = textwrap.dedent(
        """\
        a.py,sha256=4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9_v8,1
        b.py,,2
        c.py,sha384=0NHS09TV1tfY2drb3N3e3-Dh4uPk5ebn6Onq6-zt7u_w8fLz9PX29_j5-vv8_f7_,
        "commas,in,filename",,
        """
    )

    integrity_map = parse_record(text, "RECORD")

    assert integrity_map == {
        "a.py": FileIntegrity(hash=FileHash("sha256", bytes(range(224, 256))), size=1),
        "b.py": FileIntegrity(hash=None, size=2),
        "c.py": FileIntegrity(
            hash=FileHash("sha384", bytes(range(208, 256))), size=None
        ),
        "commas,in,filename": FileIntegrity(hash=None, size=None),
    }
    assert len(caplog.records) == 0


@pytest.mark.parametrize(
    "line",
    (
        "",  # empty line
        "a.py",  # too few fields (1)
        "a.py,",  # too few fields (2)
        "a.py,,,",  # too many fields
        ",,",  # missing path
        "a.py,foobar,",  # invalid hash format
        "a.py,foobar=abcde,",  # unsupported hash
        "a.py,sha256=~!@#$%,",  # invalid Base64
        "a.py,sha256=abcde,",  # also invalid Base64
        "a.py,,foobar",  # invalid size
        "a.py,,-1",  # negative size
    ),
)
def test_parse_bad_line(line: str) -> None:
    with pytest.raises(BrokenRecord, match="RECORD:1: "):
        parse_record(line + "\n", "RECORD")


@pytest.mark.parametrize(
    "digest_str",
    (
        "4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9_v8=",  # padding
        "4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v8",  # not URL-safe
        "abcdef",  # wrong size
    ),
)
def test_parse_line_with_warning(
    digest_str: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.clear()
    integrity_map = parse_record(f"a.py,sha256={digest_str},", "RECORD")
    assert caplog.records[-1].levelno == logging.WARNING
    assert "RECORD:1: " in caplog.records[-1].message

    hash = integrity_map[RecordPath("a.py")].hash
    assert hash is not None
    if len(hash.digest) == 32:
        assert hash.digest == bytes(range(224, 256))


def test_parse_duplicate_lines(caplog: pytest.LogCaptureFixture) -> None:
    text = textwrap.dedent(
        """\
        a.py,,123
        a.py,,456
        """
    )

    with pytest.raises(BrokenRecord, match="RECORD:2: "):
        parse_record(text, "RECORD")

    caplog.clear()

    text = textwrap.dedent(
        """\
        a.py,,123
        a.py,,123
        """
    )

    integrity_map = parse_record(text, "RECORD")

    assert caplog.records[-1].levelno == logging.WARNING
    assert "RECORD:2: " in caplog.records[-1].message

    assert integrity_map == {
        "a.py": FileIntegrity(hash=None, size=123),
    }


def test_serialize_record_file() -> None:
    integrity_map = {
        RecordPath("c.py"): FileIntegrity(
            hash=FileHash("sha384", bytes(range(208, 256))), size=None
        ),
        RecordPath("b.py"): FileIntegrity(hash=None, size=2),
        RecordPath("a.py"): FileIntegrity(
            hash=FileHash("sha256", bytes(range(224, 256))), size=1
        ),
        RecordPath("commas,in,filename"): FileIntegrity(hash=None, size=None),
    }

    expected_text = textwrap.dedent(
        """\
        a.py,sha256=4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9_v8,1\r
        b.py,,2\r
        c.py,sha384=0NHS09TV1tfY2drb3N3e3-Dh4uPk5ebn6Onq6-zt7u_w8fLz9PX29_j5-vv8_f7_,\r
        "commas,in,filename",,\r
        """
    )

    out_file = io.StringIO(newline="")
    serialize_record(integrity_map, out_file)

    assert out_file.getvalue() == expected_text
