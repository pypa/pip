import os
from pathlib import Path

from pip._internal.utils.filesystem import (
    _subdirs_without_generic,
    subdirs_without_files,
    subdirs_without_wheels,
)


def make_file(path: str) -> None:
    Path(path).touch()


def make_valid_symlink(path: str) -> None:
    target = path + "1"
    make_file(target)
    os.symlink(target, path)


def make_broken_symlink(path: str) -> None:
    os.symlink("foo", path)


def make_dir(path: str) -> None:
    os.mkdir(path)


class TestSubdirsWithoutGeneric:
    """Tests for _subdirs_without_generic."""

    def test_yieled_in_reverse_order(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "empty"
        deepest_dir = test_dir / "a" / "b" / "c" / "d"
        deepest_dir.mkdir(parents=True)

        result = list(
            _subdirs_without_generic(str(test_dir), lambda root, filenames: False)
        )
        assert [
            deepest_dir,
            deepest_dir.parent,
            deepest_dir.parent.parent,
            deepest_dir.parent.parent.parent,
            test_dir,
        ] == result


class TestSubdirsWithoutFiles:
    """Tests for subdirs_without_files function."""

    def test_empty_directory_tree(self, tmp_path: Path) -> None:
        """An empty directory should yield itself."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        result = list(subdirs_without_files(str(test_dir)))

        assert result == [test_dir]

    def test_directory_with_file(self, tmp_path: Path) -> None:
        """A directory with a file should not be yielded."""
        test_dir = tmp_path / "with_file"
        test_dir.mkdir()
        (test_dir / "file.txt").touch()

        result = list(subdirs_without_files(str(test_dir)))

        assert result == []

    def test_nested_empty_directories(self, tmp_path: Path) -> None:
        """Nested empty directories should all be yielded."""
        test_dir = tmp_path / "root"
        (test_dir / "a" / "b" / "c").mkdir(parents=True)
        (test_dir / "d" / "e").mkdir(parents=True)

        result = list(subdirs_without_files(str(test_dir)))

        # Should yield all directories since none have files
        assert len(result) == 6  # root, a, a/b, a/b/c, d, d/e
        assert test_dir in result

    def test_mixed_empty_and_non_empty(self, tmp_path: Path) -> None:
        """Only empty subdirectories should be yielded."""
        test_dir = tmp_path / "mixed"
        empty1 = test_dir / "empty1"
        empty2 = test_dir / "empty2"
        with_file = test_dir / "with_file"

        empty1.mkdir(parents=True)
        empty2.mkdir(parents=True)
        with_file.mkdir(parents=True)
        (with_file / "file.txt").touch()

        result = list(subdirs_without_files(str(test_dir)))

        assert empty1 in result
        assert empty2 in result
        assert with_file not in result
        assert test_dir not in result  # root has subdirs with files

    def test_deeply_nested_file_marks_parents(self, tmp_path: Path) -> None:
        """A file deep in the tree marks all parent directories as non-empty."""
        test_dir = tmp_path / "deep"
        deep_dir = test_dir / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "file.txt").touch()

        # Create another branch that's empty
        empty_branch = test_dir / "empty"
        empty_branch.mkdir()

        result = list(subdirs_without_files(str(test_dir)))

        # Only the empty branch should be yielded
        assert result == [empty_branch]

    def test_multiple_files_at_various_levels(self, tmp_path: Path) -> None:
        """Files at various levels should be handled correctly."""
        test_dir = tmp_path / "various"
        (test_dir / "a" / "b").mkdir(parents=True)
        (test_dir / "c" / "d").mkdir(parents=True)
        (test_dir / "e").mkdir(parents=True)

        # File in a/b
        (test_dir / "a" / "b" / "file1.txt").touch()
        # File in c (not in c/d)
        (test_dir / "c" / "file2.txt").touch()
        # e is empty

        result = list(subdirs_without_files(str(test_dir)))

        # Only c/d and e should be yielded (c/d has no files, e is empty)
        assert test_dir / "c" / "d" in result
        assert test_dir / "e" in result
        assert len(result) == 2


class TestSubdirsWithoutWheels:
    """Tests for subdirs_without_wheels function."""

    def test_directory_with_wheel_file(self, tmp_path: Path) -> None:
        """A directory with a .whl file should not be yielded."""
        test_dir = tmp_path / "with_wheel"
        test_dir.mkdir()
        (test_dir / "package-1.0-py3-none-any.whl").touch()

        result = list(subdirs_without_wheels(str(test_dir)))

        assert result == []

    def test_directory_with_non_wheel_files(self, tmp_path: Path) -> None:
        """A directory with non-wheel files should be yielded."""
        test_dir = tmp_path / "no_wheels"
        test_dir.mkdir()
        (test_dir / "metadata.json").touch()
        (test_dir / "readme.txt").touch()

        result = list(subdirs_without_wheels(str(test_dir)))

        assert result == [test_dir]

    def test_mixed_wheel_and_non_wheel_dirs(self, tmp_path: Path) -> None:
        """Only directories without wheels should be yielded."""
        test_dir = tmp_path / "mixed_wheels"
        has_wheel = test_dir / "has_wheel"
        no_wheel = test_dir / "no_wheel"

        has_wheel.mkdir(parents=True)
        no_wheel.mkdir(parents=True)

        (has_wheel / "package-1.0-py3-none-any.whl").touch()
        (no_wheel / "metadata.json").touch()

        result = list(subdirs_without_wheels(str(test_dir)))

        assert no_wheel in result
        assert has_wheel not in result
        assert test_dir not in result  # root has subdir with wheel

    def test_nested_wheel_marks_parents(self, tmp_path: Path) -> None:
        """A wheel file deep in the tree marks all parent directories."""
        test_dir = tmp_path / "nested_wheel"
        deep_dir = test_dir / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "package-1.0-py3-none-any.whl").touch()

        empty_branch = test_dir / "empty"
        empty_branch.mkdir()

        result = list(subdirs_without_wheels(str(test_dir)))

        # Only the empty branch should be yielded
        assert result == [empty_branch]

    def test_wheel_file_extension_matching(self, tmp_path: Path) -> None:
        """Only files ending with .whl should be considered wheels."""
        test_dir = tmp_path / "extensions"
        (test_dir / "subdir1").mkdir(parents=True)
        (test_dir / "subdir2").mkdir(parents=True)

        # Not a wheel (missing extension)
        (test_dir / "subdir1" / "package-1.0-py3-none-any").touch()
        # Not a wheel (.whl in middle of name)
        (test_dir / "subdir1" / "package.whl.backup").touch()

        # This is a wheel
        (test_dir / "subdir2" / "real-1.0-py3-none-any.whl").touch()

        result = list(subdirs_without_wheels(str(test_dir)))

        assert test_dir / "subdir1" in result
        assert test_dir / "subdir2" not in result

    def test_empty_directory_tree_no_wheels(self, tmp_path: Path) -> None:
        """Empty directories should be yielded as having no wheels."""
        test_dir = tmp_path / "empty_tree"
        (test_dir / "a" / "b").mkdir(parents=True)
        (test_dir / "c").mkdir(parents=True)

        result = list(subdirs_without_wheels(str(test_dir)))

        # All directories should be yielded since none have wheels
        assert len(result) == 4  # test_dir, a, a/b, c
        assert test_dir in result
