"""Tests for wheel helper.
"""
import csv
from email import message_from_string
from email.message import Message
from functools import partial
from zipfile import ZipFile

from tests.lib.wheel import (
    _default,
    make_metadata_file,
    make_wheel,
    make_wheel_metadata_file,
    message_from_dict,
)


def test_message_from_dict_one_value():
    message = message_from_dict({"a": "1"})
    assert set(message.get_all("a")) == {"1"}


def test_message_from_dict_multiple_values():
    message = message_from_dict({"a": ["1", "2"]})
    assert set(message.get_all("a")) == {"1", "2"}


def message_from_bytes(contents: bytes) -> Message:
    return message_from_string(contents.decode("utf-8"))


default_make_metadata = partial(
    make_metadata_file,
    name="simple",
    value=_default,
    version="0.1.0",
    updates=_default,
    body=_default,
)


def default_metadata_checks(f):
    assert f.name == "simple-0.1.0.dist-info/METADATA"
    message = message_from_bytes(f.contents)
    assert message.get_all("Metadata-Version") == ["2.1"]
    assert message.get_all("Name") == ["simple"]
    assert message.get_all("Version") == ["0.1.0"]
    return message


def test_make_metadata_file_defaults():
    f = default_make_metadata()
    default_metadata_checks(f)


def test_make_metadata_file_custom_value():
    f = default_make_metadata(updates={"a": "1"})
    message = default_metadata_checks(f)
    assert message.get_all("a") == ["1"]


def test_make_metadata_file_custom_value_list():
    f = default_make_metadata(updates={"a": ["1", "2"]})
    message = default_metadata_checks(f)
    assert set(message.get_all("a")) == {"1", "2"}


def test_make_metadata_file_custom_value_overrides():
    f = default_make_metadata(updates={"Metadata-Version": "2.2"})
    message = message_from_bytes(f.contents)
    assert message.get_all("Metadata-Version") == ["2.2"]


def test_make_metadata_file_custom_contents():
    value = b"hello"
    f = default_make_metadata(value=value)
    assert f.contents == value


tags = [("py2", "none", "any"), ("py3", "none", "any")]
default_make_wheel_metadata = partial(
    make_wheel_metadata_file,
    name="simple",
    version="0.1.0",
    value=_default,
    tags=tags,
    updates=_default,
)


def default_wheel_metadata_checks(f):
    assert f.name == "simple-0.1.0.dist-info/WHEEL"
    message = message_from_bytes(f.contents)
    assert message.get_all("Wheel-Version") == ["1.0"]
    assert message.get_all("Generator") == ["pip-test-suite"]
    assert message.get_all("Root-Is-Purelib") == ["true"]
    assert set(message.get_all("Tag")) == {"py2-none-any", "py3-none-any"}
    return message


def test_make_wheel_metadata_file_defaults():
    f = default_make_wheel_metadata()
    default_wheel_metadata_checks(f)


def test_make_wheel_metadata_file_custom_value():
    f = default_make_wheel_metadata(updates={"a": "1"})
    message = default_wheel_metadata_checks(f)
    assert message.get_all("a") == ["1"]


def test_make_wheel_metadata_file_custom_value_list():
    f = default_make_wheel_metadata(updates={"a": ["1", "2"]})
    message = default_wheel_metadata_checks(f)
    assert set(message.get_all("a")) == {"1", "2"}


def test_make_wheel_metadata_file_custom_value_override():
    f = default_make_wheel_metadata(updates={"Wheel-Version": "1.1"})
    message = message_from_bytes(f.contents)
    assert message.get_all("Wheel-Version") == ["1.1"]


def test_make_wheel_metadata_file_custom_contents():
    value = b"hello"
    f = default_make_wheel_metadata(value=value)

    assert f.name == "simple-0.1.0.dist-info/WHEEL"
    assert f.contents == value


def test_make_wheel_metadata_file_no_contents():
    f = default_make_wheel_metadata(value=None)
    assert f is None


def test_make_wheel_basics(tmpdir):
    make_wheel(name="simple", version="0.1.0").save_to_dir(tmpdir)

    expected_wheel_path = tmpdir / "simple-0.1.0-py2.py3-none-any.whl"
    assert expected_wheel_path.exists()

    with ZipFile(expected_wheel_path) as z:
        names = z.namelist()
        assert set(names) == {
            "simple-0.1.0.dist-info/METADATA",
            "simple-0.1.0.dist-info/RECORD",
            "simple-0.1.0.dist-info/WHEEL",
        }


def test_make_wheel_default_record():
    with make_wheel(
        name="simple",
        version="0.1.0",
        extra_files={"simple/__init__.py": "a"},
        extra_metadata_files={"LICENSE": "b"},
        extra_data_files={"purelib/info.txt": "c"},
    ).as_zipfile() as z:
        record_bytes = z.read("simple-0.1.0.dist-info/RECORD")
        record_text = record_bytes.decode()
        record_rows = list(csv.reader(record_text.splitlines()))
        records = {row[0]: row[1:] for row in record_rows}

        expected = {
            "simple/__init__.py": [
                "sha256=ypeBEsobvcr6wjGzmiPcTaeG7_gUfE5yuYB3ha_uSLs",
                "1",
            ],
            "simple-0.1.0.data/purelib/info.txt": [
                "sha256=Ln0sA6lQeuJl7PW1NWiFpTOTogKdJBOUmXJloaJa78Y",
                "1",
            ],
            "simple-0.1.0.dist-info/LICENSE": [
                "sha256=PiPoFgA5WUoziU9lZOGxNIu9egCI1CxKy3PurtWcAJ0",
                "1",
            ],
            "simple-0.1.0.dist-info/RECORD": ["", ""],
        }
        for name, values in expected.items():
            assert records[name] == values, name

        # WHEEL and METADATA aren't constructed in a stable way, so just spot
        # check.
        expected_variable = {
            "simple-0.1.0.dist-info/METADATA": "51",
            "simple-0.1.0.dist-info/WHEEL": "104",
        }
        for name, length in expected_variable.items():
            assert records[name][0].startswith("sha256="), name
            assert records[name][1] == length, name


def test_make_wheel_extra_files():
    with make_wheel(
        name="simple",
        version="0.1.0",
        extra_files={"simple/__init__.py": "a"},
        extra_metadata_files={"LICENSE": "b"},
        extra_data_files={"info.txt": "c"},
    ).as_zipfile() as z:
        names = z.namelist()
        assert set(names) == {
            "simple/__init__.py",
            "simple-0.1.0.data/info.txt",
            "simple-0.1.0.dist-info/LICENSE",
            "simple-0.1.0.dist-info/METADATA",
            "simple-0.1.0.dist-info/RECORD",
            "simple-0.1.0.dist-info/WHEEL",
        }

        assert z.read("simple/__init__.py") == b"a"
        assert z.read("simple-0.1.0.dist-info/LICENSE") == b"b"
        assert z.read("simple-0.1.0.data/info.txt") == b"c"


def test_make_wheel_no_files():
    with make_wheel(
        name="simple",
        version="0.1.0",
        wheel_metadata=None,
        metadata=None,
        record=None,
    ).as_zipfile() as z:
        assert not z.namelist()


def test_make_wheel_custom_files():
    with make_wheel(
        name="simple",
        version="0.1.0",
        wheel_metadata=b"a",
        metadata=b"b",
        record=b"c",
    ).as_zipfile() as z:
        assert z.read("simple-0.1.0.dist-info/WHEEL") == b"a"
        assert z.read("simple-0.1.0.dist-info/METADATA") == b"b"
        assert z.read("simple-0.1.0.dist-info/RECORD") == b"c"
