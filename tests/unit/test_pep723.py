from pathlib import Path

import pytest

from pip._internal.req.pep723 import PEP723Exception, pep723_metadata


def test_pep723_metadata_success(tmp_path: Path) -> None:
    script_content = """\
# /// script
# dependencies = [
#   "requests==2.31.0",
# ]
# ///
print("Hello world")
"""
    script_file = tmp_path / "script.py"
    script_file.write_text(script_content, encoding="utf-8")

    metadata = pep723_metadata(str(script_file))
    assert metadata == {"dependencies": ["requests==2.31.0"]}


def test_pep723_metadata_file_not_found() -> None:
    with pytest.raises(PEP723Exception) as excinfo:
        pep723_metadata("non_existent_script_12345.py")
    assert "Failed to read" in str(excinfo.value)
    assert "non_existent_script_12345.py" in str(excinfo.value)


def test_pep723_metadata_is_a_directory(tmp_path: Path) -> None:
    with pytest.raises(PEP723Exception) as excinfo:
        pep723_metadata(str(tmp_path))
    assert "Failed to read" in str(excinfo.value)


def test_pep723_metadata_invalid_toml(tmp_path: Path) -> None:
    script_content = """\
# /// script
# dependencies = [
# ///
"""
    script_file = tmp_path / "script.py"
    script_file.write_text(script_content, encoding="utf-8")

    with pytest.raises(PEP723Exception) as excinfo:
        pep723_metadata(str(script_file))
    assert "Failed to parse TOML" in str(excinfo.value)


def test_pep723_metadata_multiple_blocks(tmp_path: Path) -> None:
    script_content = """\
# /// script
# dependencies = []
# ///

# /// script
# dependencies = []
# ///
"""
    script_file = tmp_path / "script.py"
    script_file.write_text(script_content, encoding="utf-8")

    with pytest.raises(PEP723Exception) as excinfo:
        pep723_metadata(str(script_file))
    assert "Multiple 'script' blocks" in str(excinfo.value)
