import errno
import textwrap
from pathlib import Path
from typing import Any

import pytest

from pip._internal.exceptions import InstallationError
from pip._internal.req.req_dependency_group import parse_dependency_groups


def test_parse_simple_dependency_groups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = tmp_path.joinpath("pyproject.toml")
    pyproject.write_text(
        textwrap.dedent(
            """\
            [dependency-groups]
            foo = ["bar"]
            """
        )
    )
    monkeypatch.chdir(tmp_path)

    result = list(parse_dependency_groups([("pyproject.toml", "foo")]))

    assert len(result) == 1, result
    assert result[0] == "bar"


def test_parse_cyclic_dependency_groups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = tmp_path.joinpath("pyproject.toml")
    pyproject.write_text(
        textwrap.dedent(
            """\
            [dependency-groups]
            foo = [{include-group="bar"}]
            bar = [{include-group="foo"}]
            """
        )
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        InstallationError,
        match=(
            r"\[dependency-groups\] resolution failed for "
            r"'foo' from 'pyproject\.toml':"
        ),
    ) as excinfo:
        parse_dependency_groups([("pyproject.toml", "foo")])

    exception = excinfo.value
    assert (
        "Cyclic dependency group include while resolving foo: foo -> bar, bar -> foo"
    ) in str(exception)


def test_parse_with_no_dependency_groups_defined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = tmp_path.joinpath("pyproject.toml")
    pyproject.write_text("")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        InstallationError,
        match=(r"\[dependency-groups\] table was missing from 'pyproject\.toml'\."),
    ):
        parse_dependency_groups([("pyproject.toml", "foo")])


def test_parse_with_no_pyproject_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(InstallationError, match=r"pyproject\.toml not found\."):
        parse_dependency_groups([("pyproject.toml", "foo")])


def test_parse_with_malformed_pyproject_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = tmp_path.joinpath("pyproject.toml")
    pyproject.write_text(
        textwrap.dedent(
            """\
            [dependency-groups  # no closing bracket
            foo = ["bar"]
            """
        )
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(InstallationError, match=r"Error parsing pyproject\.toml"):
        parse_dependency_groups([("pyproject.toml", "foo")])


def test_parse_gets_unexpected_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = tmp_path.joinpath("pyproject.toml")
    pyproject.write_text(
        textwrap.dedent(
            """\
            [dependency-groups]
            foo = ["bar"]
            """
        )
    )
    monkeypatch.chdir(tmp_path)

    # inject an implementation of `tomli.load()` which emits an 'OSError(EPIPE, ...)'
    # as though we were loading from a fifo or other unusual filetype
    def epipe_toml_load(*args: Any, **kwargs: Any) -> None:
        raise OSError(errno.EPIPE, "Broken pipe")

    monkeypatch.setattr(
        "pip._internal.req.req_dependency_group.tomli.load", epipe_toml_load
    )

    with pytest.raises(InstallationError, match=r"Error reading pyproject\.toml"):
        parse_dependency_groups([("pyproject.toml", "foo")])
