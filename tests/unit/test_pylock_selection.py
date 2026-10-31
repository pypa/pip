from __future__ import annotations

import sys
from pathlib import Path

import pytest
import tomli_w

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.pylock import (
    Package,
    PackageDirectory,
    PackageWheel,
    Pylock,
)
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.cli.req_command import _pylock_source_key
from pip._internal.commands.install import InstallCommand
from pip._internal.exceptions import InstallationError
from pip._internal.network.session import PipSession
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.pylock import (
    is_valid_pylock_filename,
    package_directory_requirement_url,
    package_wheel_requirement_url,
    select_from_pylock_path_or_url,
)

from tests.lib import make_test_finder


@pytest.mark.parametrize(
    "source",
    [
        "http://example.com/pylock.toml",
        "HTTPS://example.com/pylock.dev.toml?download=1#fragment",
        "file:///tmp/pylock.toml",
        "file:/tmp/pylock.toml",
        "https:/example.com/pylock.toml",
    ],
)
def test_pylock_filename_url_policy(source: str) -> None:
    assert is_valid_pylock_filename(source)
    assert is_valid_pylock_filename(source, allow_urls=True)
    assert not is_valid_pylock_filename(source, allow_urls=False)


@pytest.mark.parametrize("allow_urls", [False, True])
def test_pylock_filename_rejects_malformed_url(allow_urls: bool) -> None:
    assert not is_valid_pylock_filename(
        "https://[invalid/pylock.toml", allow_urls=allow_urls
    )


@pytest.mark.parametrize("allow_urls", [False, True])
@pytest.mark.parametrize(
    "filename,expected",
    [("pylock.toml", True), ("pylock.dev.toml", True), ("requirements.txt", False)],
)
def test_pylock_filename_local_path_policy(
    tmp_path: Path, filename: str, expected: bool, allow_urls: bool
) -> None:
    assert (
        is_valid_pylock_filename(str(tmp_path / filename), allow_urls=allow_urls)
        is expected
    )


def write_lock(
    path: Path,
    packages: list[tuple[str, str, str | None]],
    *,
    defaults: tuple[str, ...] = ("runtime",),
) -> Path:
    """Write wheel records whose markers exercise lock selection without downloads."""
    lock = Pylock(
        lock_version=Version("1.0"),
        created_by="pip",
        extras=[canonicalize_name("extra-only"), canonicalize_name("shared")],
        dependency_groups=["dev", "docs", "Lint_Tools", "shared"],
        default_groups=list(defaults),
        packages=[
            Package(
                name=canonicalize_name(name),
                version=Version(version),
                marker=Marker(marker) if marker is not None else None,
                wheels=[
                    PackageWheel(
                        path=f"{name.replace('-', '_')}-{version}-py3-none-any.whl",
                        hashes={"sha256": "0" * 64},
                    )
                ],
            )
            for name, version, marker in packages
        ],
    )
    path.write_text(tomli_w.dumps(lock.to_dict()), encoding="utf-8")
    return path


@pytest.fixture
def selection_lock(tmp_path: Path) -> Path:
    """Build a lock whose selected groups can switch package versions."""
    return write_lock(
        tmp_path / "pylock.toml",
        [
            ("always", "1", None),
            ("runtime", "1", "'runtime' in dependency_groups"),
            ("switch", "1", "'dev' not in dependency_groups"),
            ("switch", "2", "'dev' in dependency_groups"),
            (
                "intersection",
                "1",
                "'dev' in dependency_groups and 'docs' in dependency_groups",
            ),
            ("extra-shared", "1", "'shared' in extras"),
            ("group-shared", "1", "'shared' in dependency_groups"),
            ("lint", "1", "'lint-tools' in dependency_groups"),
        ],
    )


@pytest.mark.parametrize(
    "groups,include_defaults,expected",
    [
        ((), True, [("always", "1"), ("runtime", "1"), ("switch", "1")]),
        (("dev",), False, [("always", "1"), ("switch", "2")]),
        (
            ("dev", "docs"),
            True,
            [("always", "1"), ("runtime", "1"), ("switch", "2"), ("intersection", "1")],
        ),
        (
            ("shared",),
            False,
            [
                ("always", "1"),
                ("switch", "1"),
                ("group-shared", "1"),
            ],
        ),
        (
            ("LINT_tools",),
            False,
            [("always", "1"), ("switch", "1"), ("lint", "1")],
        ),
    ],
)
def test_select_pylock_context(
    selection_lock: Path,
    groups: tuple[str, ...],
    include_defaults: bool,
    expected: list[tuple[str, str]],
) -> None:
    with PipSession() as session:
        selected = select_from_pylock_path_or_url(
            str(selection_lock),
            session,
            format_control=None,
            dependency_groups=groups,
            include_default_groups=include_defaults,
        )
        assert [
            (package.name, str(package.version)) for package, _ in selected
        ] == expected


@pytest.mark.parametrize(
    "groups,name",
    [
        (("unknown",), "unknown"),
        (("runtime",), "runtime"),
        (("extra-only",), "extra-only"),
    ],
)
def test_select_pylock_rejects_unavailable_names(
    selection_lock: Path,
    groups: tuple[str, ...],
    name: str,
) -> None:
    with PipSession() as session, pytest.raises(InstallationError) as exc_info:
        list(
            select_from_pylock_path_or_url(
                str(selection_lock),
                session,
                format_control=None,
                dependency_groups=groups,
            )
        )
    assert name in str(exc_info.value)
    assert repr(str(selection_lock)) in str(exc_info.value)
    assert "lint-tools" in str(exc_info.value)


def test_select_pylock_escapes_group_names_in_errors(tmp_path: Path) -> None:
    path = tmp_path / "pylock.toml"
    lock = Pylock(
        lock_version=Version("1.0"),
        created_by="pip",
        dependency_groups=["\x1b[31mavailable"],
        packages=[],
    )
    path.write_text(tomli_w.dumps(lock.to_dict()), encoding="utf-8")

    with PipSession() as session, pytest.raises(InstallationError) as exc_info:
        list(
            select_from_pylock_path_or_url(
                str(path),
                session,
                format_control=None,
                dependency_groups=["\x1b[2Jrequested"],
            )
        )

    message = str(exc_info.value)
    assert "\x1b" not in message
    assert "\\x1b" in message


def test_select_pylock_default_group_can_also_be_public(tmp_path: Path) -> None:
    path = write_lock(
        tmp_path / "pylock.toml",
        [("package", "1", "'dev' in dependency_groups")],
        defaults=("dev",),
    )
    with PipSession() as session:
        selected = list(
            select_from_pylock_path_or_url(
                str(path),
                session,
                format_control=None,
                dependency_groups=["dev"],
                include_default_groups=False,
            )
        )

    assert [(package.name, str(package.version)) for package, _ in selected] == [
        ("package", "1")
    ]


def get_requirements(arguments: list[str]) -> list[InstallRequirement]:
    """Collect command inputs through the production parser and package finder."""
    command = InstallCommand(name="install", summary="")
    command.parser.set_defaults(dependency_groups=[])
    options, args = command.parse_args(arguments)
    with PipSession() as session:
        finder = make_test_finder(session=session)
        return command.get_requirements(args, options, finder, session)


@pytest.mark.parametrize("prefix", ["file://", "file:", "FILE:"])
def test_pylock_file_url_preserves_artifact_base(
    selection_lock: Path, prefix: str
) -> None:
    source = selection_lock.as_uri().replace("file://", prefix, 1)

    with PipSession() as session:
        selected = list(
            select_from_pylock_path_or_url(source, session, format_control=None)
        )

    wheel = selected[0][1]
    assert isinstance(wheel, PackageWheel)
    assert (
        package_wheel_requirement_url(source, wheel)
        == (selection_lock.parent / "always-1-py3-none-any.whl").as_uri()
    )
    assert (
        package_directory_requirement_url(source, PackageDirectory(path="project"))
        == (selection_lock.parent / "project").as_uri() + "/"
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_pylock_merges_repeated_source_requests(
    selection_lock: Path, monkeypatch: pytest.MonkeyPatch, reverse: bool
) -> None:
    monkeypatch.chdir(selection_lock.parent)
    requests = [
        ("-r", "pylock.toml"),
        ("-r", str(selection_lock)),
        ("--group", "./pylock.toml:dev"),
        ("--group", f"{selection_lock}:docs"),
        ("--group", "pylock.toml:dev"),
    ]
    if reverse:
        requests.reverse()
    arguments = [argument for request in requests for argument in request]

    requirements = get_requirements(arguments)

    assert [str(requirement.req) for requirement in requirements] == [
        "always==1",
        "runtime==1",
        "switch==2",
        "intersection==1",
    ]
    assert all(requirement.user_supplied for requirement in requirements)
    assert all(
        requirement.hash_options == {"sha256": ["0" * 64]}
        for requirement in requirements
    )


@pytest.mark.parametrize(
    "selectors,include_defaults",
    [
        (["-r", "pylock.toml[shared,extra-only]", "--group", "pylock.toml:dev"], True),
        (
            [
                "-r",
                "pylock.toml[shared]",
                "-r",
                "./pylock.toml[extra-only]",
                "--group",
                "pylock.toml:dev",
            ],
            True,
        ),
        (["--group", "pylock.toml[shared,extra-only]:dev"], False),
        (
            [
                "--group",
                "pylock.toml[shared]:dev",
                "--group",
                "./pylock.toml[extra-only]:docs",
                "--group",
                "pylock.toml:dev",
            ],
            False,
        ),
    ],
)
def test_pylock_extras_and_groups_share_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selectors: list[str],
    include_defaults: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_lock(
        tmp_path / "pylock.toml",
        [
            ("always", "1", None),
            (
                "combined",
                "1",
                "'shared' in extras and 'extra-only' in extras "
                "and 'dev' in dependency_groups",
            ),
            ("runtime", "1", "'runtime' in dependency_groups"),
            (
                "default-combined",
                "1",
                "'runtime' in dependency_groups "
                "and 'dev' in dependency_groups and 'shared' in extras",
            ),
        ],
    )

    requirements = get_requirements(selectors)

    expected = ["always==1", "combined==1"]
    if include_defaults:
        expected.extend(["runtime==1", "default-combined==1"])
    assert [str(requirement.req) for requirement in requirements] == expected


def test_pylock_source_key_preserves_path_case(tmp_path: Path) -> None:
    upper = tmp_path / "A" / "pylock.toml"
    lower = tmp_path / "a" / "pylock.toml"

    assert _pylock_source_key(str(upper)) != _pylock_source_key(str(lower))


def test_pylock_keeps_separate_source_conflicts(selection_lock: Path) -> None:
    other_lock = selection_lock.with_name("pylock.other.toml")
    write_lock(other_lock, [("always", "2", None)])

    with pytest.raises(
        InstallationError, match="Multiple locked links provided for always"
    ):
        get_requirements(["--group", f"{selection_lock}:dev", "-r", str(other_lock)])


@pytest.mark.skipif(
    sys.platform == "win32", reason="Directory symlinks require privileges"
)
def test_pylock_parent_after_symlink_preserves_source_identity(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    elsewhere = tmp_path / "elsewhere"
    child = elsewhere / "child"
    child.mkdir(parents=True)
    (project / "link").symlink_to(child, target_is_directory=True)
    first = write_lock(project / "pylock.toml", [("package", "1", None)])
    write_lock(elsewhere / "pylock.toml", [("package", "2", None)])
    second = project / "link" / ".." / "pylock.toml"

    with pytest.raises(
        InstallationError, match="Multiple locked links provided for package"
    ):
        get_requirements(["-r", str(second), "--group", f"{first}:dev"])


@pytest.mark.skipif(sys.platform == "win32", reason="File symlinks require privileges")
def test_pylock_symlink_keeps_distinct_artifact_bases(selection_lock: Path) -> None:
    other_directory = selection_lock.parent / "other"
    other_directory.mkdir()
    alias = other_directory / "pylock.toml"
    alias.symlink_to(selection_lock)

    with pytest.raises(
        InstallationError, match="Multiple locked links provided for always"
    ):
        get_requirements(["-r", str(selection_lock), "--group", f"{alias}:dev"])


@pytest.mark.parametrize("invalid_first", [False, True])
def test_pylock_trailing_separator_keeps_distinct_artifact_base(
    selection_lock: Path, invalid_first: bool
) -> None:
    invalid_source = f"{selection_lock}/"
    sources = [str(selection_lock), invalid_source]
    if invalid_first:
        sources.reverse()

    with pytest.raises(
        InstallationError, match="Multiple locked links provided for always"
    ) as exc_info:
        get_requirements(
            [argument for source in sources for argument in ("-r", source)]
        )

    assert f"{selection_lock.as_uri()}/always-1-py3-none-any.whl" in str(exc_info.value)


@pytest.mark.parametrize(
    "project_path",
    [
        "pyproject.toml",
        pytest.param(
            "file:project/pyproject.toml",
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="Colons are not valid in Windows filenames",
            ),
        ),
        pytest.param(
            "https:project/pyproject.toml",
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="Colons are not valid in Windows filenames",
            ),
        ),
        pytest.param(
            "http://[local/pyproject.toml",
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="Colons are not valid in Windows filenames",
            ),
        ),
    ],
)
def test_pylock_preserves_explicit_pyproject_group(
    selection_lock: Path, monkeypatch: pytest.MonkeyPatch, project_path: str
) -> None:
    monkeypatch.chdir(selection_lock.parent)
    pyproject = Path(project_path)
    pyproject.parent.mkdir(parents=True, exist_ok=True)
    pyproject.write_text('[dependency-groups]\ndev = ["project-dependency"]\n')

    requirements = get_requirements(
        ["--group", f"{project_path}:dev", "--group", "pylock.toml:dev"]
    )

    assert {str(requirement.req) for requirement in requirements} == {
        "always==1",
        "switch==2",
        "project-dependency",
    }


@pytest.mark.parametrize("lock_option", ["-r", "--group"])
def test_pylock_preserves_implicit_pyproject_group(
    selection_lock: Path, lock_option: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(selection_lock.parent)
    Path("pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["project-dependency"]\n'
    )
    lock_argument = str(selection_lock)
    if lock_option == "--group":
        lock_argument += ":dev"

    requirements = get_requirements([lock_option, lock_argument, "--group", "dev"])

    expected = {"always==1", "project-dependency"}
    if lock_option == "-r":
        expected.update(["runtime==1", "switch==1"])
    else:
        expected.add("switch==2")
    assert {str(requirement.req) for requirement in requirements} == expected


def test_requirements_brackets_preserve_literal_filename(tmp_path: Path) -> None:
    requirements_path = tmp_path / "requirements.txt[dev]"
    requirements_path.write_text("ordinary-dependency==1\n")

    requirements = get_requirements(["-r", str(requirements_path)])

    assert [str(requirement.req) for requirement in requirements] == [
        "ordinary-dependency==1"
    ]


@pytest.mark.parametrize(
    "source",
    ["https://example.com/pylock.toml", "file:///pylock.toml", "file:/tmp/pylock.toml"],
)
def test_pylock_groups_reject_url_sources(source: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        get_requirements(["--group", f"{source}:dev"])
    assert exc_info.value.code == 2


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX double-leading-slash path")
def test_local_lock_path_is_not_parsed_as_url() -> None:
    with pytest.raises(InstallationError, match="Error reading pylock file"):
        get_requirements(["-r", "//[team]/share/pylock.toml"])


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory names")
@pytest.mark.parametrize(
    "directory", ["ht\ttp:", "f\tile:", "git+https://project", "custom://project"]
)
def test_local_lock_path_is_not_a_supported_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: str
) -> None:
    monkeypatch.chdir(tmp_path)
    lock_directory = tmp_path / directory
    lock_directory.mkdir(parents=True)
    write_lock(
        lock_directory / "pylock.toml", [("package", "1", "'dev' in dependency_groups")]
    )

    def unexpected_fetch(_session: PipSession, source: str) -> None:
        pytest.fail(f"Local lock path fetched through the session: {source!r}")

    monkeypatch.setattr(PipSession, "get", unexpected_fetch)
    requirements = get_requirements(["--group", f"{directory}/pylock.toml:dev"])

    assert [str(requirement.req) for requirement in requirements] == ["package==1"]


@pytest.mark.parametrize("lock_first", [False, True])
def test_pylock_fetch_preserves_requirements_file_options(
    selection_lock: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lock_first: bool,
) -> None:
    requirements_file = tmp_path / "trusted.txt"
    requirements_file.write_text("--trusted-host example.com\nordinary-dependency\n")
    observed_origins = []

    def get_content(source: str, session: PipSession) -> str:
        """Observe the real session state when the remote lock would be fetched."""
        assert source == "https://example.com/pylock.toml"
        observed_origins.append(list(session.pip_trusted_origins))
        return selection_lock.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "pip._internal.utils.pylock._get_pylock_path_or_url_content", get_content
    )
    requests = [
        ("-r", str(requirements_file)),
        ("-r", "https://example.com/pylock.toml"),
    ]
    if lock_first:
        requests.reverse()

    get_requirements([argument for request in requests for argument in request])

    assert observed_origins == ([[]] if lock_first else [[("example.com", None)]])


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows path parsing")
@pytest.mark.parametrize(
    "path",
    [
        r"C:\project\pylock.toml",
        r"C:\project\pylock.test.toml",
        "C://project/pylock.toml",
    ],
)
def test_pylock_group_windows_drive_path(path: str) -> None:
    command = InstallCommand(name="install", summary="")
    command.parser.set_defaults(dependency_groups=[])

    options, _ = command.parse_args(["--group", f"{path}:dev"])

    assert options.dependency_groups == [(path, "dev")]
