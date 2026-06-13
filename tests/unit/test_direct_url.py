import pytest

from pip._internal.models.direct_url import (
    ArchiveInfo,
    DirectUrl,
    DirectUrlValidationError,
    VcsInfo,
)


def test_from_json() -> None:
    json = '{"url": "file:///home/user/project", "dir_info": {}}'
    direct_url = DirectUrl.from_json(json)
    assert direct_url.url == "file:///home/user/project"
    assert direct_url.dir_info
    assert not direct_url.dir_info.editable


def test_to_json() -> None:
    direct_url = DirectUrl(
        url="file:///home/user/archive.tgz",
        archive_info=ArchiveInfo(),
    )
    direct_url.validate()
    assert direct_url.to_json() == (
        '{"archive_info": {}, "url": "file:///home/user/archive.tgz"}'
    )


def test_archive_info() -> None:
    direct_url_dict = {
        "url": "file:///home/user/archive.tgz",
        "archive_info": {"hash": "sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220"},
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert direct_url.archive_info
    assert direct_url.url == direct_url_dict["url"]
    # test we add the hashes key automatically
    assert direct_url.archive_info.hashes == {
        "sha1": "1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    }


def test_dir_info() -> None:
    direct_url_dict = {
        "url": "file:///home/user/project",
        "dir_info": {"editable": True},
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert direct_url.dir_info
    assert direct_url.url == direct_url_dict["url"]
    assert direct_url.dir_info.editable is True
    assert direct_url.to_dict_compat() == direct_url_dict
    # test editable default to False
    direct_url_dict = {"url": "file:///home/user/project", "dir_info": {}}
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert direct_url.dir_info
    assert not direct_url.dir_info.editable


def test_vcs_info() -> None:
    direct_url_dict = {
        "url": "https:///g.c/u/p.git",
        "vcs_info": {
            "vcs": "git",
            "requested_revision": "master",
            "commit_id": "1b8c5bc61a86f377fea47b4276c8c8a5842d2220",
        },
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert direct_url.vcs_info
    assert direct_url.url == direct_url_dict["url"]
    assert direct_url.vcs_info.vcs == "git"
    assert direct_url.vcs_info.requested_revision == "master"
    assert direct_url.vcs_info.commit_id == "1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    assert direct_url.to_dict_compat() == direct_url_dict


def test_parsing_validation() -> None:
    with pytest.raises(
        DirectUrlValidationError, match="Missing required value in 'url'"
    ):
        DirectUrl.from_dict({"dir_info": {}})
    with pytest.raises(
        DirectUrlValidationError,
        match="Exactly one of vcs_info, archive_info, dir_info must be present",
    ):
        DirectUrl.from_dict({"url": "http://..."})
    with pytest.raises(
        DirectUrlValidationError,
        match=r"Unexpected type str \(expected bool\) in 'dir_info\.editable'",
    ):
        DirectUrl.from_dict({"url": "http://...", "dir_info": {"editable": "false"}})
    with pytest.raises(
        DirectUrlValidationError,
        match=r"Unexpected type int \(expected str\) in 'archive_info\.hash'",
    ):
        DirectUrl.from_dict({"url": "http://...", "archive_info": {"hash": 1}})
    with pytest.raises(
        DirectUrlValidationError, match=r"Missing required value in 'vcs_info\.vcs'"
    ):
        DirectUrl.from_dict({"url": "http://...", "vcs_info": {"vcs": None}})
    with pytest.raises(
        DirectUrlValidationError,
        match=r"Missing required value in 'vcs_info\.commit_id'",
    ):
        DirectUrl.from_dict({"url": "http://...", "vcs_info": {"vcs": "git"}})
    with pytest.raises(
        DirectUrlValidationError,
        match="Exactly one of vcs_info, archive_info, dir_info must be present",
    ):
        DirectUrl.from_dict({"url": "http://...", "dir_info": {}, "archive_info": {}})
    with pytest.raises(
        DirectUrlValidationError,
        match=(
            r"Invalid hash format \(expected '<algorithm>=<hash>'\) "
            r"in 'archive_info\.hash'"
        ),
    ):
        DirectUrl.from_dict(
            {"url": "http://...", "archive_info": {"hash": "sha256:aaa"}}
        )


def test_redact_url() -> None:
    def _redact_git(url: str) -> str:
        direct_url = DirectUrl(
            url=url,
            vcs_info=VcsInfo(vcs="git", commit_id="1"),
        )
        return direct_url.to_dict()["url"]

    def _redact_archive(url: str) -> str:
        direct_url = DirectUrl(
            url=url,
            archive_info=ArchiveInfo(),
        )
        return direct_url.to_dict()["url"]

    assert (
        _redact_git("https://user:password@g.c/u/p.git@branch#egg=pkg")
        == "https://g.c/u/p.git@branch#egg=pkg"
    )
    assert _redact_git("https://${USER}:password@g.c/u/p.git") == "https://g.c/u/p.git"
    assert (
        _redact_archive("file://${U}:${PIP_PASSWORD}@g.c/u/p.tgz")
        == "file://${U}:${PIP_PASSWORD}@g.c/u/p.tgz"
    )
    assert (
        _redact_git("https://${PIP_TOKEN}@g.c/u/p.git")
        == "https://${PIP_TOKEN}@g.c/u/p.git"
    )
    assert _redact_git("ssh://git@g.c/u/p.git") == "ssh://git@g.c/u/p.git"
