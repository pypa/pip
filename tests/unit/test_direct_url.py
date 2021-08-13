import pytest

from pip._internal.models.direct_url import (
    ArchiveInfo,
    DirectUrl,
    DirectUrlValidationError,
    DirInfo,
    VcsInfo,
)


def test_from_json():
    json = '{"url": "file:///home/user/project", "dir_info": {}}'
    direct_url = DirectUrl.from_json(json)
    assert direct_url.url == "file:///home/user/project"
    assert direct_url.info.editable is False


def test_to_json():
    direct_url = DirectUrl(
        url="file:///home/user/archive.tgz",
        info=ArchiveInfo(),
    )
    direct_url.validate()
    assert direct_url.to_json() == (
        '{"archive_info": {}, "url": "file:///home/user/archive.tgz"}'
    )


def test_archive_info():
    direct_url_dict = {
        "url": "file:///home/user/archive.tgz",
        "archive_info": {"hash": "sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220"},
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert isinstance(direct_url.info, ArchiveInfo)
    assert direct_url.url == direct_url_dict["url"]
    assert direct_url.info.hash == direct_url_dict["archive_info"]["hash"]
    assert direct_url.to_dict() == direct_url_dict


def test_dir_info():
    direct_url_dict = {
        "url": "file:///home/user/project",
        "dir_info": {"editable": True},
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert isinstance(direct_url.info, DirInfo)
    assert direct_url.url == direct_url_dict["url"]
    assert direct_url.info.editable is True
    assert direct_url.to_dict() == direct_url_dict
    # test editable default to False
    direct_url_dict = {"url": "file:///home/user/project", "dir_info": {}}
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert direct_url.info.editable is False


def test_vcs_info():
    direct_url_dict = {
        "url": "https:///g.c/u/p.git",
        "vcs_info": {
            "vcs": "git",
            "requested_revision": "master",
            "commit_id": "1b8c5bc61a86f377fea47b4276c8c8a5842d2220",
        },
    }
    direct_url = DirectUrl.from_dict(direct_url_dict)
    assert isinstance(direct_url.info, VcsInfo)
    assert direct_url.url == direct_url_dict["url"]
    assert direct_url.info.vcs == "git"
    assert direct_url.info.requested_revision == "master"
    assert direct_url.info.commit_id == "1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    assert direct_url.to_dict() == direct_url_dict


def test_parsing_validation():
    with pytest.raises(DirectUrlValidationError, match="url must have a value"):
        DirectUrl.from_dict({"dir_info": {}})
    with pytest.raises(
        DirectUrlValidationError,
        match="missing one of archive_info, dir_info, vcs_info",
    ):
        DirectUrl.from_dict({"url": "http://..."})
    with pytest.raises(DirectUrlValidationError, match="unexpected type for editable"):
        DirectUrl.from_dict({"url": "http://...", "dir_info": {"editable": "false"}})
    with pytest.raises(DirectUrlValidationError, match="unexpected type for hash"):
        DirectUrl.from_dict({"url": "http://...", "archive_info": {"hash": 1}})
    with pytest.raises(DirectUrlValidationError, match="unexpected type for vcs"):
        DirectUrl.from_dict({"url": "http://...", "vcs_info": {"vcs": None}})
    with pytest.raises(DirectUrlValidationError, match="commit_id must have a value"):
        DirectUrl.from_dict({"url": "http://...", "vcs_info": {"vcs": "git"}})
    with pytest.raises(
        DirectUrlValidationError,
        match="more than one of archive_info, dir_info, vcs_info",
    ):
        DirectUrl.from_dict({"url": "http://...", "dir_info": {}, "archive_info": {}})


def test_redact_url():
    def _redact_git(url):
        direct_url = DirectUrl(
            url=url,
            info=VcsInfo(vcs="git", commit_id="1"),
        )
        return direct_url.redacted_url

    def _redact_archive(url):
        direct_url = DirectUrl(
            url=url,
            info=ArchiveInfo(),
        )
        return direct_url.redacted_url

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
