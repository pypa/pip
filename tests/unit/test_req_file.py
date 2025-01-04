import collections
import logging
import os
import re
import textwrap
from optparse import Values
from pathlib import Path
from typing import Any, Iterator, List, Optional, Protocol, Tuple, Union
from unittest import mock

import pytest

import pip._internal.req.req_file  # this will be monkeypatched
from pip._internal.exceptions import InstallationError, RequirementsFileParseError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.format_control import FormatControl
from pip._internal.network.session import PipSession
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
    install_req_from_parsed_requirement,
)
from pip._internal.req.req_file import (
    break_args_options,
    ignore_comments,
    join_lines,
    parse_requirements,
    preprocess,
)
from pip._internal.req.req_install import InstallRequirement

from tests.lib import TestData, make_test_finder, requirements_file


@pytest.fixture
def session() -> PipSession:
    return PipSession()


@pytest.fixture
def finder(session: PipSession) -> PackageFinder:
    return make_test_finder(session=session)


@pytest.fixture
def options(session: PipSession) -> mock.Mock:
    return mock.Mock(
        isolated_mode=False,
        index_url="default_url",
        format_control=FormatControl(set(), set()),
        features_enabled=[],
    )


def parse_reqfile(
    filename: Union[Path, str],
    session: PipSession,
    finder: Optional[PackageFinder] = None,
    options: Optional[Values] = None,
    constraint: bool = False,
    isolated: bool = False,
) -> Iterator[InstallRequirement]:
    # Wrap parse_requirements/install_req_from_parsed_requirement to
    # avoid having to write the same chunk of code in lots of tests.
    for parsed_req in parse_requirements(
        os.fspath(filename),
        session,
        finder=finder,
        options=options,
        constraint=constraint,
    ):
        yield install_req_from_parsed_requirement(
            parsed_req,
            isolated=isolated,
            config_settings=(
                parsed_req.options.get("config_settings")
                if parsed_req.options
                else None
            ),
        )


def test_read_file_url(tmp_path: Path, session: PipSession) -> None:
    reqs = tmp_path.joinpath("requirements.txt")
    reqs.write_text("foo")
    result = list(parse_requirements(reqs.as_posix(), session))

    assert len(result) == 1, result
    assert result[0].requirement == "foo"

    # The comes_from value has three parts: -r or -c flag, path, and line.
    # The path value in the middle needs some special logic due to our path
    # normalization logic.
    assert result[0].comes_from[:3] == "-r "
    assert result[0].comes_from[-9:] == " (line 1)"
    assert os.path.samefile(result[0].comes_from[3:-9], str(reqs))


class TestPreprocess:
    """tests for `preprocess`"""

    def test_comments_and_joins_case1(self) -> None:
        content = textwrap.dedent(
            """\
          req1 \\
          # comment \\
          req2
        """
        )
        result = preprocess(content)
        assert list(result) == [(1, "req1"), (3, "req2")]

    def test_comments_and_joins_case2(self) -> None:
        content = textwrap.dedent(
            """\
          req1\\
          # comment
        """
        )
        result = preprocess(content)
        assert list(result) == [(1, "req1")]

    def test_comments_and_joins_case3(self) -> None:
        content = textwrap.dedent(
            """\
          req1 \\
          # comment
          req2
        """
        )
        result = preprocess(content)
        assert list(result) == [(1, "req1"), (3, "req2")]


class TestIgnoreComments:
    """tests for `ignore_comment`"""

    def test_ignore_line(self) -> None:
        lines = [(1, ""), (2, "req1"), (3, "req2")]
        result = ignore_comments(lines)
        assert list(result) == [(2, "req1"), (3, "req2")]

    def test_ignore_comment(self) -> None:
        lines = [(1, "req1"), (2, "# comment"), (3, "req2")]
        result = ignore_comments(lines)
        assert list(result) == [(1, "req1"), (3, "req2")]

    def test_strip_comment(self) -> None:
        lines = [(1, "req1"), (2, "req # comment"), (3, "req2")]
        result = ignore_comments(lines)
        assert list(result) == [(1, "req1"), (2, "req"), (3, "req2")]


class TestJoinLines:
    """tests for `join_lines`"""

    def test_join_lines(self) -> None:
        lines = enumerate(
            [
                "line 1",
                "line 2:1 \\",
                "line 2:2",
                "line 3:1 \\",
                "line 3:2 \\",
                "line 3:3",
                "line 4",
            ],
            start=1,
        )
        expect = [
            (1, "line 1"),
            (2, "line 2:1 line 2:2"),
            (4, "line 3:1 line 3:2 line 3:3"),
            (7, "line 4"),
        ]
        assert expect == list(join_lines(lines))

    def test_last_line_with_escape(self) -> None:
        lines = enumerate(
            [
                "line 1",
                "line 2 \\",
            ],
            start=1,
        )
        expect = [
            (1, "line 1"),
            (2, "line 2 "),
        ]
        assert expect == list(join_lines(lines))


class LineProcessor(Protocol):
    def __call__(
        self,
        line: str,
        filename: str,
        line_number: int,
        finder: Optional[PackageFinder] = None,
        options: Optional[Values] = None,
        session: Optional[PipSession] = None,
        constraint: bool = False,
    ) -> List[InstallRequirement]: ...


@pytest.fixture
def line_processor(monkeypatch: pytest.MonkeyPatch, tmpdir: Path) -> LineProcessor:
    def process_line(
        line: str,
        filename: str,
        line_number: int,
        finder: Optional[PackageFinder] = None,
        options: Optional[Values] = None,
        session: Optional[PipSession] = None,
        constraint: bool = False,
    ) -> List[InstallRequirement]:
        if session is None:
            session = PipSession()

        prefix = "\n" * (line_number - 1)
        path = tmpdir.joinpath(filename)
        path.parent.mkdir(exist_ok=True)
        path.write_text(prefix + line)
        monkeypatch.chdir(str(tmpdir))
        return list(
            parse_reqfile(
                filename,
                finder=finder,
                options=options,
                session=session,
                constraint=constraint,
                isolated=options.isolated_mode if options else False,
            )
        )

    return process_line


class TestProcessLine:
    """tests for `process_line`"""

    def test_parser_error(self, line_processor: LineProcessor) -> None:
        with pytest.raises(RequirementsFileParseError):
            line_processor("--bogus", "file", 1)

    def test_parser_offending_line(self, line_processor: LineProcessor) -> None:
        line = "pkg==1.0.0 --hash=somehash"
        with pytest.raises(RequirementsFileParseError) as err:
            line_processor(line, "file", 1)
        assert line in str(err.value)

    def test_parser_non_offending_line(self, line_processor: LineProcessor) -> None:
        try:
            line_processor("pkg==1.0.0 --hash=sha256:somehash", "file", 1)
        except RequirementsFileParseError:
            pytest.fail("Reported offending line where it should not.")

    def test_only_one_req_per_line(self, line_processor: LineProcessor) -> None:
        # pkg_resources raises the ValueError
        with pytest.raises(InstallationError):
            line_processor("req1 req2", "file", 1)

    def test_error_message(self, line_processor: LineProcessor) -> None:
        """
        Test the error message if a parsing error occurs (all of path,
        line number, and hint).
        """
        with pytest.raises(InstallationError) as exc:
            line_processor(
                "my-package=1.0", filename="path/requirements.txt", line_number=3
            )

        expected = (
            "Invalid requirement: 'my-package=1.0': "
            "Expected end or semicolon (after name and no valid version specifier)\n"
            "    my-package=1.0\n"
            "              ^ (from line 3 of path/requirements.txt)\n"
            "Hint: = is not a valid operator. Did you mean == ?"
        )
        assert str(exc.value) == expected

    def test_yield_line_requirement(self, line_processor: LineProcessor) -> None:
        line = "SomeProject"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_line(line, comes_from=comes_from)
        assert repr(line_processor(line, filename, 1)[0]) == repr(req)

    def test_yield_pep440_line_requirement(self, line_processor: LineProcessor) -> None:
        line = "SomeProject @ https://url/SomeProject-py2-py3-none-any.whl"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_line(line, comes_from=comes_from)
        assert repr(line_processor(line, filename, 1)[0]) == repr(req)

    def test_yield_line_constraint(self, line_processor: LineProcessor) -> None:
        line = "SomeProject"
        filename = "filename"
        comes_from = f"-c {filename} (line {1})"
        req = install_req_from_line(line, comes_from=comes_from, constraint=True)
        found_req = line_processor(line, filename, 1, constraint=True)[0]
        assert repr(found_req) == repr(req)
        assert found_req.constraint is True

    def test_yield_line_requirement_with_spaces_in_specifier(
        self, line_processor: LineProcessor
    ) -> None:
        line = "SomeProject >= 2"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_line(line, comes_from=comes_from)
        assert repr(line_processor(line, filename, 1)[0]) == repr(req)
        assert req.req is not None
        assert str(req.req.specifier) == ">=2"

    def test_yield_editable_requirement(self, line_processor: LineProcessor) -> None:
        url = "git+https://url#egg=SomeProject"
        line = f"-e {url}"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_editable(url, comes_from=comes_from)
        assert repr(line_processor(line, filename, 1)[0]) == repr(req)

    def test_yield_editable_constraint(self, line_processor: LineProcessor) -> None:
        url = "git+https://url#egg=SomeProject"
        line = f"-e {url}"
        filename = "filename"
        comes_from = f"-c {filename} (line {1})"
        req = install_req_from_editable(url, comes_from=comes_from, constraint=True)
        found_req = line_processor(line, filename, 1, constraint=True)[0]
        assert repr(found_req) == repr(req)
        assert found_req.constraint is True

    def test_nested_constraints_file(
        self, monkeypatch: pytest.MonkeyPatch, tmpdir: Path, session: PipSession
    ) -> None:
        req_name = "hello"
        req_file = tmpdir / "parent" / "req_file.txt"
        req_file.parent.mkdir()
        req_file.write_text("-c reqs.txt")
        req_file.parent.joinpath("reqs.txt").write_text(req_name)

        monkeypatch.chdir(str(tmpdir))

        reqs = list(parse_reqfile("./parent/req_file.txt", session=session))
        assert len(reqs) == 1
        assert reqs[0].name == req_name
        assert reqs[0].constraint

    def test_repeated_requirement_files(
        self, tmp_path: Path, session: PipSession
    ) -> None:
        # Test that the same requirements file can be included multiple times
        # as long as there is no recursion. https://github.com/pypa/pip/issues/13046
        tmp_path.joinpath("a.txt").write_text("requests")
        tmp_path.joinpath("b.txt").write_text("-r a.txt")
        tmp_path.joinpath("c.txt").write_text("-r a.txt\n-r b.txt")
        parsed = parse_requirements(
            filename=os.fspath(tmp_path.joinpath("c.txt")), session=session
        )
        assert [r.requirement for r in parsed] == ["requests", "requests"]

    def test_recursive_requirements_file(
        self, tmpdir: Path, session: PipSession
    ) -> None:
        req_files: list[Path] = []
        req_file_count = 4
        for i in range(req_file_count):
            req_file = tmpdir / f"{i}.txt"
            req_file.write_text(f"-r {(i+1) % req_file_count}.txt")
            req_files.append(req_file)

        # When the passed requirements file recursively references itself
        with pytest.raises(
            RequirementsFileParseError,
            match=(
                f"{re.escape(str(req_files[0]))} recursively references itself"
                f" in {re.escape(str(req_files[req_file_count - 1]))}"
            ),
        ):
            list(parse_requirements(filename=str(req_files[0]), session=session))

        # When one of other the requirements file recursively references itself
        req_files[req_file_count - 1].write_text(
            # Just name since they are in the same folder
            f"-r {req_files[req_file_count - 2].name}"
        )
        with pytest.raises(
            RequirementsFileParseError,
            match=(
                f"{re.escape(str(req_files[req_file_count - 2]))} recursively"
                " references itself in"
                f" {re.escape(str(req_files[req_file_count - 1]))} and again in"
                f" {re.escape(str(req_files[req_file_count - 3]))}"
            ),
        ):
            list(parse_requirements(filename=str(req_files[0]), session=session))

    def test_recursive_relative_requirements_file(
        self, tmpdir: Path, session: PipSession
    ) -> None:
        root_req_file = tmpdir / "root.txt"
        (tmpdir / "nest" / "nest").mkdir(parents=True)
        level_1_req_file = tmpdir / "nest" / "level_1.txt"
        level_2_req_file = tmpdir / "nest" / "nest" / "level_2.txt"

        root_req_file.write_text("-r nest/level_1.txt")
        level_1_req_file.write_text("-r nest/level_2.txt")
        level_2_req_file.write_text("-r ../../root.txt")

        with pytest.raises(
            RequirementsFileParseError,
            match=(
                f"{re.escape(str(root_req_file))} recursively references itself in"
                f" {re.escape(str(level_2_req_file))}"
            ),
        ):
            list(parse_requirements(filename=str(root_req_file), session=session))

    def test_options_on_a_requirement_line(self, line_processor: LineProcessor) -> None:
        line = (
            'SomeProject --global-option="yo3" --global-option "yo4" '
            '--config-settings="yo3=yo4" --config-settings "yo1=yo2"'
        )
        filename = "filename"
        req = line_processor(line, filename, 1)[0]
        assert req.global_options == ["yo3", "yo4"]
        assert req.config_settings == {"yo3": "yo4", "yo1": "yo2"}

    def test_hash_options(self, line_processor: LineProcessor) -> None:
        """Test the --hash option: mostly its value storage.

        Make sure it reads and preserve multiple hashes.

        """
        line = (
            "SomeProject --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b1"
            "61e5c1fa7425e73043362938b9824 "
            "--hash=sha384:59e1748777448c69de6b800d7a33bbfb9ff1b463e44354c"
            "3553bcdb9c666fa90125a3c79f90397bdf5f6a13de828684f "
            "--hash=sha256:486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8"
            "e5a6c65260e9cb8a7"
        )
        filename = "filename"
        req = line_processor(line, filename, 1)[0]
        assert req.hash_options == {
            "sha256": [
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
                "486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7",
            ],
            "sha384": [
                "59e1748777448c69de6b800d7a33bbfb9ff1b463e44354c3553bcd"
                "b9c666fa90125a3c79f90397bdf5f6a13de828684f"
            ],
        }

    def test_set_isolated(
        self, line_processor: LineProcessor, options: mock.Mock
    ) -> None:
        line = "SomeProject"
        filename = "filename"
        options.isolated_mode = True
        result = line_processor(line, filename, 1, options=options)
        assert result[0].isolated

    def test_set_finder_no_index(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--no-index", "file", 1, finder=finder)
        assert finder.index_urls == []

    def test_set_finder_no_index_is_remembered_for_later_invocations(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--no-index", "file", 1, finder=finder)
        line_processor("--index-url=url", "file", 1, finder=finder)
        assert finder.index_urls == []

    def test_set_finder_index_url(
        self, line_processor: LineProcessor, finder: PackageFinder, session: PipSession
    ) -> None:
        line_processor("--index-url=url", "file", 1, finder=finder, session=session)
        assert finder.index_urls == ["url"]
        assert session.auth.index_urls == ["url"]

    def test_set_finder_find_links(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--find-links=url", "file", 1, finder=finder)
        assert finder.find_links == ["url"]

    def test_set_finder_extra_index_urls(
        self, line_processor: LineProcessor, finder: PackageFinder, session: PipSession
    ) -> None:
        line_processor(
            "--extra-index-url=url", "file", 1, finder=finder, session=session
        )
        assert finder.index_urls == ["url"]
        assert session.auth.index_urls == ["url"]

    def test_set_finder_trusted_host(
        self,
        line_processor: LineProcessor,
        caplog: pytest.LogCaptureFixture,
        session: PipSession,
        finder: PackageFinder,
    ) -> None:
        with caplog.at_level(logging.INFO):
            line_processor(
                "--trusted-host=host1 --trusted-host=host2:8080",
                "file.txt",
                1,
                finder=finder,
                session=session,
            )
        assert list(finder.trusted_hosts) == ["host1", "host2:8080"]
        session = finder._link_collector.session
        assert session.adapters["https://host1/"] is session._trusted_host_adapter
        assert session.adapters["https://host2:8080/"] is session._trusted_host_adapter

        # Test the log message.
        actual = [(r.levelname, r.message) for r in caplog.records]
        expected = ("INFO", "adding trusted host: 'host1' (from line 1 of file.txt)")
        assert expected in actual

    def test_set_finder_allow_all_prereleases(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--pre", "file", 1, finder=finder)
        assert finder.allow_all_prereleases

    def test_use_feature(
        self, line_processor: LineProcessor, options: mock.Mock
    ) -> None:
        """--use-feature can be set in requirements files."""
        line_processor("--use-feature=fast-deps", "filename", 1, options=options)

    def test_use_feature_with_error(
        self, line_processor: LineProcessor, options: mock.Mock
    ) -> None:
        """--use-feature triggers error when parsing requirements files."""
        with pytest.raises(RequirementsFileParseError):
            line_processor("--use-feature=resolvelib", "filename", 1, options=options)

    def test_relative_local_find_links(
        self,
        line_processor: LineProcessor,
        finder: PackageFinder,
        monkeypatch: pytest.MonkeyPatch,
        tmpdir: Path,
    ) -> None:
        """
        Test a relative find_links path is joined with the req file directory
        """
        base_path = tmpdir / "path"

        def normalize(path: Path) -> str:
            return os.path.normcase(os.path.abspath(os.path.normpath(str(path))))

        # Make sure the test also passes on windows
        req_file = normalize(base_path / "req_file.txt")
        nested_link = normalize(base_path / "rel_path")
        exists_ = os.path.exists

        def exists(path: str) -> bool:
            if path == nested_link:
                return True
            else:
                return exists_(path)

        monkeypatch.setattr(os.path, "exists", exists)
        line_processor("--find-links=rel_path", req_file, 1, finder=finder)
        assert finder.find_links == [nested_link]

    def test_relative_http_nested_req_files(
        self,
        finder: PackageFinder,
        session: PipSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Test a relative nested req file path is joined with the req file url
        """
        req_name = "hello"
        req_file = "http://me.com/me/req_file.txt"

        def get_file_content(
            filename: str, *args: Any, **kwargs: Any
        ) -> Tuple[None, str]:
            if filename == req_file:
                return None, "-r reqs.txt"
            elif filename == "http://me.com/me/reqs.txt":
                return None, req_name
            pytest.fail(f"Unexpected file requested {filename}")

        monkeypatch.setattr(
            pip._internal.req.req_file, "get_file_content", get_file_content
        )

        result = list(parse_reqfile(req_file, session=session))
        assert len(result) == 1
        assert result[0].name == req_name
        assert not result[0].constraint

    def test_relative_local_nested_req_files(
        self, session: PipSession, monkeypatch: pytest.MonkeyPatch, tmpdir: Path
    ) -> None:
        """
        Test a relative nested req file path is joined with the req file dir
        """
        req_name = "hello"
        req_file = tmpdir / "parent" / "req_file.txt"
        req_file.parent.mkdir()
        req_file.write_text("-r reqs.txt")
        req_file.parent.joinpath("reqs.txt").write_text(req_name)

        monkeypatch.chdir(str(tmpdir))

        reqs = list(parse_reqfile("./parent/req_file.txt", session=session))
        assert len(reqs) == 1
        assert reqs[0].name == req_name
        assert not reqs[0].constraint

    def test_absolute_local_nested_req_files(
        self, session: PipSession, tmpdir: Path
    ) -> None:
        """
        Test an absolute nested req file path
        """
        req_name = "hello"
        req_file = tmpdir / "parent" / "req_file.txt"
        req_file.parent.mkdir()
        other_req_file = tmpdir / "other" / "reqs.txt"
        other_req_file.parent.mkdir()
        # POSIX-ify the path, since Windows backslashes aren't supported.
        other_req_file_str = str(other_req_file).replace("\\", "/")

        req_file.write_text(f"-r {other_req_file_str}")
        other_req_file.write_text(req_name)

        reqs = list(parse_reqfile(str(req_file), session=session))
        assert len(reqs) == 1
        assert reqs[0].name == req_name
        assert not reqs[0].constraint

    def test_absolute_http_nested_req_file_in_local(
        self, session: PipSession, monkeypatch: pytest.MonkeyPatch, tmpdir: Path
    ) -> None:
        """
        Test a nested req file url in a local req file
        """
        req_name = "hello"
        req_file = tmpdir / "req_file.txt"
        nested_req_file = "http://me.com/me/req_file.txt"

        def get_file_content(
            filename: str, *args: Any, **kwargs: Any
        ) -> Tuple[None, str]:
            if filename == str(req_file):
                return None, f"-r {nested_req_file}"
            elif filename == nested_req_file:
                return None, req_name
            pytest.fail(f"Unexpected file requested {filename}")

        monkeypatch.setattr(
            pip._internal.req.req_file, "get_file_content", get_file_content
        )

        result = list(parse_reqfile(req_file, session=session))
        assert len(result) == 1
        assert result[0].name == req_name
        assert not result[0].constraint


class TestBreakOptionsArgs:
    def test_no_args(self) -> None:
        assert ("", "--option") == break_args_options("--option")

    def test_no_options(self) -> None:
        assert ("arg arg", "") == break_args_options("arg arg")

    def test_args_short_options(self) -> None:
        result = break_args_options("arg arg -s")
        assert ("arg arg", "-s") == result

    def test_args_long_options(self) -> None:
        result = break_args_options("arg arg --long")
        assert ("arg arg", "--long") == result


class TestOptionVariants:
    # this suite is really just testing optparse, but added it anyway

    def test_variant1(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("-i url", "file", 1, finder=finder)
        assert finder.index_urls == ["url"]

    def test_variant2(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("-i 'url'", "file", 1, finder=finder)
        assert finder.index_urls == ["url"]

    def test_variant3(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--index-url=url", "file", 1, finder=finder)
        assert finder.index_urls == ["url"]

    def test_variant4(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--index-url url", "file", 1, finder=finder)
        assert finder.index_urls == ["url"]

    def test_variant5(
        self, line_processor: LineProcessor, finder: PackageFinder
    ) -> None:
        line_processor("--index-url='url'", "file", 1, finder=finder)
        assert finder.index_urls == ["url"]


class TestParseRequirements:
    """tests for `parse_reqfile`"""

    @pytest.mark.network
    def test_remote_reqs_parse(self) -> None:
        """
        Test parsing a simple remote requirements file
        """
        # this requirements file just contains a comment previously this has
        # failed in py3: https://github.com/pypa/pip/issues/760
        for _ in parse_reqfile(
            "https://raw.githubusercontent.com/pypa/"
            "pip-test-package/master/"
            "tests/req_just_comment.txt",
            session=PipSession(),
        ):
            pass

    def test_multiple_appending_options(
        self, tmpdir: Path, finder: PackageFinder, options: mock.Mock
    ) -> None:
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("--extra-index-url url1 \n")
            fp.write("--extra-index-url url2 ")

        list(
            parse_reqfile(
                tmpdir.joinpath("req1.txt"),
                finder=finder,
                session=PipSession(),
                options=options,
            )
        )

        assert finder.index_urls == ["url1", "url2"]

    def test_expand_existing_env_variables(
        self, tmpdir: Path, finder: PackageFinder
    ) -> None:
        template = "https://{}:x-oauth-basic@github.com/user/{}/archive/master.zip"

        def make_var(name: str) -> str:
            return f"${{{name}}}"

        env_vars = collections.OrderedDict(
            [
                ("GITHUB_TOKEN", "notarealtoken"),
                ("DO_12_FACTOR", "awwyeah"),
            ]
        )

        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write(template.format(*map(make_var, env_vars)))

        # Construct the session outside the monkey-patch, since it access the
        # env
        session = PipSession()
        with mock.patch("pip._internal.req.req_file.os.getenv") as getenv:
            getenv.side_effect = lambda n: env_vars[n]

            reqs = list(
                parse_reqfile(
                    tmpdir.joinpath("req1.txt"), finder=finder, session=session
                )
            )

        assert len(reqs) == 1, "parsing requirement file with env variable failed"

        expected_url = template.format(*env_vars.values())
        assert reqs[0].link is not None
        assert reqs[0].link.url == expected_url, "variable expansion in req file failed"

    def test_expand_missing_env_variables(
        self, tmpdir: Path, finder: PackageFinder
    ) -> None:
        req_url = (
            "https://${NON_EXISTENT_VARIABLE}:$WRONG_FORMAT@"
            "%WINDOWS_FORMAT%github.com/user/repo/archive/master.zip"
        )

        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write(req_url)

        # Construct the session outside the monkey-patch, since it access the
        # env
        session = PipSession()
        with mock.patch("pip._internal.req.req_file.os.getenv") as getenv:
            getenv.return_value = ""

            reqs = list(
                parse_reqfile(
                    tmpdir.joinpath("req1.txt"), finder=finder, session=session
                )
            )

            assert len(reqs) == 1, "parsing requirement file with env variable failed"
            assert reqs[0].link is not None
            assert (
                reqs[0].link.url == req_url
            ), "ignoring invalid env variable in req file failed"

    def test_join_lines(self, tmpdir: Path, finder: PackageFinder) -> None:
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("--extra-index-url url1 \\\n--extra-index-url url2")

        list(
            parse_reqfile(
                tmpdir.joinpath("req1.txt"), finder=finder, session=PipSession()
            )
        )

        assert finder.index_urls == ["url1", "url2"]

    def test_req_file_parse_no_only_binary(
        self, data: TestData, finder: PackageFinder
    ) -> None:
        list(
            parse_reqfile(
                data.reqfiles.joinpath("supported_options2.txt"),
                finder=finder,
                session=PipSession(),
            )
        )
        expected = FormatControl({"fred"}, {"wilma"})
        assert finder.format_control == expected

    def test_req_file_parse_comment_start_of_line(
        self, tmpdir: Path, finder: PackageFinder
    ) -> None:
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("# Comment ")

        reqs = list(
            parse_reqfile(
                tmpdir.joinpath("req1.txt"), finder=finder, session=PipSession()
            )
        )

        assert not reqs

    def test_invalid_options(self, tmpdir: Path, finder: PackageFinder) -> None:
        """
        Test parsing invalid options such as missing closing quotation
        """
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("--'data\n")

        with pytest.raises(RequirementsFileParseError):
            list(
                parse_reqfile(
                    tmpdir.joinpath("req1.txt"), finder=finder, session=PipSession()
                )
            )

    def test_req_file_parse_comment_end_of_line_with_url(
        self, tmpdir: Path, finder: PackageFinder
    ) -> None:
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("https://example.com/foo.tar.gz # Comment ")

        reqs = list(
            parse_reqfile(
                tmpdir.joinpath("req1.txt"), finder=finder, session=PipSession()
            )
        )

        assert len(reqs) == 1
        assert reqs[0].link is not None
        assert reqs[0].link.url == "https://example.com/foo.tar.gz"

    def test_req_file_parse_egginfo_end_of_line_with_url(
        self, tmpdir: Path, finder: PackageFinder
    ) -> None:
        """
        Test parsing comments in a requirements file
        """
        with open(tmpdir.joinpath("req1.txt"), "w") as fp:
            fp.write("https://example.com/foo.tar.gz#egg=wat")

        reqs = list(
            parse_reqfile(
                tmpdir.joinpath("req1.txt"), finder=finder, session=PipSession()
            )
        )

        assert len(reqs) == 1
        assert reqs[0].name == "wat"

    def test_req_file_no_finder(self, tmpdir: Path) -> None:
        """
        Test parsing a requirements file without a finder
        """
        with open(tmpdir.joinpath("req.txt"), "w") as fp:
            fp.write(
                """
    --find-links https://example.com/
    --index-url https://example.com/
    --extra-index-url https://two.example.com/
    --no-use-wheel
    --no-index
            """
            )

        parse_reqfile(tmpdir.joinpath("req.txt"), session=PipSession())

    def test_install_requirements_with_options(
        self,
        tmpdir: Path,
        finder: PackageFinder,
        session: PipSession,
        options: mock.Mock,
    ) -> None:
        global_option = "--dry-run"

        content = f"""
        --only-binary :all:
        INITools==2.0 --global-option="{global_option}"
        """

        with requirements_file(content, tmpdir) as reqs_file:
            req = next(
                parse_reqfile(
                    reqs_file.resolve(), finder=finder, options=options, session=session
                )
            )

        assert req.global_options == [global_option]
