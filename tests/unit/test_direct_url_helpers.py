import os
from functools import partial
from pathlib import Path
from unittest import mock

from pip._internal.models.direct_url import ArchiveInfo, DirectUrl, DirInfo, VcsInfo
from pip._internal.models.link import Link
from pip._internal.utils.direct_url_helpers import (
    direct_url_as_pep440_direct_reference,
    direct_url_from_link,
)
from pip._internal.vcs.git import Git


def test_as_pep440_requirement_archive() -> None:
    direct_url = DirectUrl(
        url="file:///home/user/archive.tgz",
        info=ArchiveInfo(),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ file:///home/user/archive.tgz"
    )
    direct_url.subdirectory = "subdir"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ file:///home/user/archive.tgz#subdirectory=subdir"
    )
    assert isinstance(direct_url.info, ArchiveInfo)
    direct_url.info.hash = "sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ file:///home/user/archive.tgz"
        "#sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220&subdirectory=subdir"
    )


def test_as_pep440_requirement_dir() -> None:
    direct_url = DirectUrl(
        url="file:///home/user/project",
        info=DirInfo(editable=False),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ file:///home/user/project"
    )


def test_as_pep440_requirement_editable_dir() -> None:
    # direct_url_as_pep440_direct_reference behaves the same
    # irrespective of the editable flag. It's the responsibility of
    # callers to render it as editable
    direct_url = DirectUrl(
        url="file:///home/user/project",
        info=DirInfo(editable=True),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ file:///home/user/project"
    )


def test_as_pep440_requirement_vcs() -> None:
    direct_url = DirectUrl(
        url="https:///g.c/u/p.git",
        info=VcsInfo(vcs="git", commit_id="1b8c5bc61a86f377fea47b4276c8c8a5842d2220"),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ git+https:///g.c/u/p.git"
        "@1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    )
    direct_url.subdirectory = "subdir"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg")
        == "pkg @ git+https:///g.c/u/p.git"
        "@1b8c5bc61a86f377fea47b4276c8c8a5842d2220#subdirectory=subdir"
    )


@mock.patch("pip._internal.vcs.git.Git.get_revision")
def test_from_link_vcs(mock_get_backend_for_scheme: mock.Mock) -> None:
    _direct_url_from_link = partial(direct_url_from_link, source_dir="...")
    direct_url = _direct_url_from_link(Link("git+https://g.c/u/p.git"))
    assert direct_url.url == "https://g.c/u/p.git"
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.vcs == "git"
    direct_url = _direct_url_from_link(Link("git+https://g.c/u/p.git#egg=pkg"))
    assert direct_url.url == "https://g.c/u/p.git"
    direct_url = _direct_url_from_link(
        Link("git+https://g.c/u/p.git#egg=pkg&subdirectory=subdir")
    )
    assert direct_url.url == "https://g.c/u/p.git"
    assert direct_url.subdirectory == "subdir"
    direct_url = _direct_url_from_link(Link("git+https://g.c/u/p.git@branch"))
    assert direct_url.url == "https://g.c/u/p.git"
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.requested_revision == "branch"
    direct_url = _direct_url_from_link(Link("git+https://g.c/u/p.git@branch#egg=pkg"))
    assert direct_url.url == "https://g.c/u/p.git"
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.requested_revision == "branch"
    direct_url = _direct_url_from_link(Link("git+https://token@g.c/u/p.git"))
    assert direct_url.to_dict()["url"] == "https://g.c/u/p.git"


def test_from_link_vcs_with_source_dir_obtains_commit_id(tmpdir: Path) -> None:
    repo_path = tmpdir / "test-repo"
    repo_path.mkdir()
    repo_dir = os.fspath(repo_path)
    Git.run_command(["init"], cwd=repo_dir)
    (repo_path / "somefile").touch()
    Git.run_command(["add", "."], cwd=repo_dir)
    Git.run_command(["commit", "-m", "commit msg"], cwd=repo_dir)
    commit_id = Git.get_revision(repo_dir)
    direct_url = direct_url_from_link(
        Link("git+https://g.c/u/p.git"), source_dir=repo_dir
    )
    assert direct_url.url == "https://g.c/u/p.git"
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.commit_id == commit_id


def test_from_link_vcs_without_source_dir() -> None:
    direct_url = direct_url_from_link(
        Link("git+https://g.c/u/p.git@1"), link_is_in_wheel_cache=True
    )
    assert direct_url.url == "https://g.c/u/p.git"
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.info.commit_id == "1"


def test_from_link_archive() -> None:
    direct_url = direct_url_from_link(Link("https://g.c/archive.tgz"))
    assert direct_url.url == "https://g.c/archive.tgz"
    assert isinstance(direct_url.info, ArchiveInfo)
    direct_url = direct_url_from_link(
        Link("https://g.c/archive.tgz#sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220")
    )
    assert isinstance(direct_url.info, ArchiveInfo)
    assert direct_url.info.hash == "sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    # Test the hashes key has been automatically populated.
    assert direct_url.info.hashes == {
        "sha1": "1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    }


def test_from_link_dir(tmpdir: Path) -> None:
    dir_url = tmpdir.as_uri()
    direct_url = direct_url_from_link(Link(dir_url))
    assert direct_url.url == dir_url
    assert isinstance(direct_url.info, DirInfo)


def test_from_link_hide_user_password() -> None:
    # Basic test only here, other variants are covered by
    # direct_url.redact_url tests.
    direct_url = direct_url_from_link(
        Link("git+https://user:password@g.c/u/p.git@branch#egg=pkg"),
        link_is_in_wheel_cache=True,
    )
    assert direct_url.to_dict()["url"] == "https://g.c/u/p.git"
    direct_url = direct_url_from_link(
        Link("git+ssh://git@g.c/u/p.git@branch#egg=pkg"),
        link_is_in_wheel_cache=True,
    )
    assert direct_url.to_dict()["url"] == "ssh://git@g.c/u/p.git"
